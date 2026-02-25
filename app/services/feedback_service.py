"""
app/services/feedback_service.py — Recruiter feedback storage and weight adaptation.

Implements an incremental learning loop WITHOUT model retraining:
- Stores recruiter accept/reject decisions per ranking entry
- After FEEDBACK_THRESHOLD decisions for a job, computes weight adjustments
- Adjustment strategy: Exponential Moving Average (EMA) on factor scores
  of accepted vs rejected candidates

Design rationale:
- Full retraining is expensive and brittle with small feedback samples
- EMA is stable, explainable, and continuously improving
- Weights are clamped to [MIN_WEIGHT, MAX_WEIGHT] to prevent degenerate scoring
- Weight history is logged for auditability
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    # pyre-ignore[21]: Pyre fails to resolve root config
    import config
except ImportError:
    import sys
    import os
    # Ensure root is in path for both runtime and type checking
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if root_path not in sys.path:
        sys.path.append(root_path)
    # pyre-ignore[21]: Pyre fails to resolve root config
    import config

logger = logging.getLogger(__name__)


def store_feedback(
    conn: sqlite3.Connection,
    ranking_id: int,
    job_id: int,
    resume_id: int,
    decision: str,
    notes: Optional[str] = None,
) -> int:
    """
    Persist a recruiter feedback entry to the database.
    Returns the new feedback row id.
    """
    cursor = conn.execute(
        """
        INSERT INTO feedback (ranking_id, job_id, resume_id, decision, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (ranking_id, job_id, resume_id, decision, notes, datetime.utcnow().isoformat()),
    )
    conn.commit()
    feedback_id = cursor.lastrowid
    logger.info(
        f"Feedback stored | id={feedback_id} | job_id={job_id} "
        f"| resume_id={resume_id} | decision={decision}"
    )
    return int(feedback_id) if feedback_id is not None else 0


def get_feedback_count_for_job(conn: sqlite3.Connection, job_id: int) -> int:
    """Return total feedback entries for a given job."""
    row = conn.execute(
        "SELECT COUNT(*) FROM feedback WHERE job_id = ?", (job_id,)
    ).fetchone()
    return row[0] if row else 0


def get_feedback_stats(conn: sqlite3.Connection, job_id: Optional[int] = None) -> dict[str, Any]:
    """
    Return feedback statistics, optionally filtered by job.
    Counts unique candidates (latest decision) to avoid total summary inflation.
    """
    where_clause = ""
    params = []
    if job_id is not None:
        where_clause = "WHERE job_id = ?"
        params = [job_id]

    # Subquery to get the latest decision for each unique (job_id, resume_id) pair
    latest_decisions_query = """
        SELECT decision, job_id
        FROM feedback
        WHERE id IN (
            SELECT MAX(id)
            FROM feedback
            GROUP BY job_id, resume_id
        )
    """

    stats_row = conn.execute(f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN decision = 'accept' THEN 1 ELSE 0 END) as accepts
        FROM ({latest_decisions_query})
        {where_clause}
    """, params).fetchone()

    total = stats_row["total"] if stats_row and stats_row["total"] is not None else 0
    accept = stats_row["accepts"] if stats_row and stats_row["accepts"] is not None else 0
    reject = total - accept

    # Breakdown by job (always global or filtered)
    by_job_rows = conn.execute(f"""
        SELECT job_id, decision, COUNT(*) as cnt
        FROM ({latest_decisions_query})
        {where_clause}
        GROUP BY job_id, decision
        ORDER BY job_id
    """, params).fetchall()

    feedback_by_job: dict[int, dict] = {}
    for row in by_job_rows:
        jid = int(row["job_id"]) if row["job_id"] is not None else 0
        if jid not in feedback_by_job:
            feedback_by_job[jid] = {"job_id": jid, "accept": 0, "reject": 0}
        feedback_by_job[jid][str(row["decision"])] = int(row["cnt"]) if row["cnt"] is not None else 0

    weight_adjustments_row = conn.execute(
        "SELECT COUNT(*) FROM weight_history WHERE trigger = 'feedback'"
        + (f" AND job_id = ?" if job_id is not None else ""),
        params
    ).fetchone()
    weight_adjustments = weight_adjustments_row[0] if weight_adjustments_row else 0

    return {
        "total_feedback": int(total),
        "accept_count": int(accept),
        "reject_count": int(reject),
        "acceptance_rate": float(int((float(accept) / max(1.0, float(total))) * 10000) / 10000.0),
        "feedback_by_job": list(feedback_by_job.values()),
        "weight_adjustments_triggered": int(weight_adjustments),
    }


def _get_current_weights(conn: sqlite3.Connection, job_id: int) -> dict[str, float]:
    """
    Fetch current scoring weights for a job.
    Falls back to the job's stored weights, then to defaults.
    """
    # pyre-ignore[21]: Pyre fails to resolve root config
    from config import DEFAULT_SCORING_WEIGHTS

    row = conn.execute(
        "SELECT weights_json FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()

    if row and row["weights_json"]:
        try:
            return json.loads(row["weights_json"])
        except json.JSONDecodeError:
            pass

    return dict(DEFAULT_SCORING_WEIGHTS)


def _compute_adjusted_weights(
    current_weights: dict[str, float],
    accepted_scores: list[dict[str, float]],
    rejected_scores: list[dict[str, float]],
    learning_rate: float,
    min_weight: float,
    max_weight: float,
) -> dict[str, float]:
    """
    Adjust weights using EMA signal from accepted vs rejected candidate scores.

    Algorithm:
    1. For accepted candidates, identify which factors scored highest → boost those weights
    2. For rejected candidates, identify which factors were dominant → reduce those weights
    3. Apply EMA step: new_weight = current + lr * signal
    4. Re-normalize weights to sum to 1.0
    5. Clamp to [min_weight, max_weight]
    """
    factors = ["skill_match", "experience_alignment", "role_relevance"]

    def avg_factor(scores_list: list[dict[str, float]], factor: str) -> float:
        if not scores_list:
            return 0.0
        return sum(s.get(factor, 0.0) for s in scores_list) / len(scores_list)

    new_weights = dict(current_weights)

    for factor in factors:
        avg_accept = avg_factor(accepted_scores, factor)
        avg_reject = avg_factor(rejected_scores, factor)

        # Signal: positive if accepted candidates scored high on this factor
        # Negative if rejected candidates scored high (bad signal factor)
        signal = avg_accept - avg_reject

        # EMA update
        new_weights[factor] = current_weights.get(factor, 0.33) + learning_rate * signal

    # Clamp to valid range
    new_weights = {
        k: max(min_weight, min(max_weight, v))
        for k, v in new_weights.items()
    }

    # Re-normalize to sum to 1.0
    total = sum(new_weights.values())
    if total > 0:
        new_weights = {k: float(int(float(v / total) * 10000) / 10000.0) for k, v in new_weights.items()}

    logger.info(
        f"Weight adjustment computed | "
        f"old={current_weights} → new={new_weights}"
    )
    return new_weights


def _save_updated_weights(
    conn: sqlite3.Connection,
    job_id: int,
    weights: dict[str, float],
    trigger: str = "feedback",
) -> None:
    """Persist updated weights to job record and weight_history audit log."""
    weights_json = json.dumps(weights)

    conn.execute(
        "UPDATE jobs SET weights_json = ? WHERE id = ?",
        (weights_json, job_id),
    )
    conn.execute(
        """
        INSERT INTO weight_history (job_id, weights_json, trigger, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (job_id, weights_json, trigger, datetime.utcnow().isoformat()),
    )
    conn.commit()
    logger.info(f"Weights saved for job_id={job_id}: {weights}")


def maybe_trigger_weight_adjustment(
    conn: sqlite3.Connection,
    job_id: int,
) -> Optional[dict[str, float]]:
    """
    Check if enough feedback has accumulated to trigger weight adjustment.
    If yes, compute and persist new weights. Returns new weights or None.

    Called after every feedback submission.
    """
    # pyre-ignore[21]: Pyre fails to resolve root config
    from config import FEEDBACK_THRESHOLD, WEIGHT_LEARNING_RATE, MIN_WEIGHT, MAX_WEIGHT

    feedback_count = get_feedback_count_for_job(conn, job_id)
    if feedback_count == 0 or feedback_count % FEEDBACK_THRESHOLD != 0:
        return None  # not enough feedback yet

    logger.info(
        f"Triggering weight adjustment for job_id={job_id} "
        f"(feedback count: {feedback_count})"
    )

    # Fetch accepted and rejected score breakdowns
    accepted_rows = conn.execute(
        """
        SELECT r.score_breakdown_json
        FROM feedback f
        JOIN rankings r ON r.id = f.ranking_id
        WHERE f.job_id = ? AND f.decision = 'accept'
        """,
        (job_id,),
    ).fetchall()

    rejected_rows = conn.execute(
        """
        SELECT r.score_breakdown_json
        FROM feedback f
        JOIN rankings r ON r.id = f.ranking_id
        WHERE f.job_id = ? AND f.decision = 'reject'
        """,
        (job_id,),
    ).fetchall()

    def parse_scores(rows) -> list[dict[str, float]]:
        result = []
        for row in rows:
            try:
                result.append(json.loads(row["score_breakdown_json"]))
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    accepted_scores = parse_scores(accepted_rows)
    rejected_scores = parse_scores(rejected_rows)

    current_weights = _get_current_weights(conn, job_id)

    new_weights = _compute_adjusted_weights(
        current_weights=current_weights,
        accepted_scores=accepted_scores,
        rejected_scores=rejected_scores,
        learning_rate=WEIGHT_LEARNING_RATE,
        min_weight=MIN_WEIGHT,
        max_weight=MAX_WEIGHT,
    )

    _save_updated_weights(conn, job_id, new_weights, trigger="feedback")
    return new_weights
