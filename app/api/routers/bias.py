"""
app/api/routers/bias.py — Bias analysis endpoint.
"""

import json
import sqlite3
from fastapi import APIRouter, Depends, HTTPException  # type: ignore

from app.api.dependencies import get_db  # type: ignore
from app.services.bias_service import analyze_bias  # type: ignore

router = APIRouter()


@router.get("/{job_id}")
def get_bias_report(job_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Generate a bias analysis report for the most recent ranking of a job.

    Analyzes:
    - Experience-YoE skew (Spearman correlation between YoE and rank)
    - Keyword overfit (does skill_match score predict total rank?)
    - Factor dominance (which scoring dimension drives rankings?)

    Returns signals with severity levels and ethical disclaimer.
    """
    job_row = db.execute(
        "SELECT id, title, weights_json FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()
    if not job_row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    ranking_rows = db.execute(
        """
        SELECT r.resume_id, r.rank, r.total_score,
               r.score_breakdown_json, r.matched_skills_json,
               res.parsed_json
        FROM rankings r
        JOIN resumes res ON res.id = r.resume_id
        WHERE r.job_id = ?
        ORDER BY r.rank ASC
        """,
        (job_id,),
    ).fetchall()

    if not ranking_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No rankings found for job {job_id}. Run POST /rank/{job_id} first.",
        )

    # Build ranked_candidates list for bias analysis
    ranked_candidates = []
    for row in ranking_rows:
        parsed = json.loads(row["parsed_json"])
        ranked_candidates.append({
            "resume_id": row["resume_id"],
            "rank": row["rank"],
            "total_score": row["total_score"],
            "score_breakdown": json.loads(row["score_breakdown_json"]),
            "matched_skills": json.loads(row["matched_skills_json"]),
            "candidate_years_experience": parsed.get("total_years_experience", 0.0),
        })

    weights = json.loads(job_row["weights_json"])

    report = analyze_bias(
        ranked_candidates=ranked_candidates,
        job_id=job_id,
        job_title=job_row["title"],
        weights=weights,
    )

    # Persist bias report
    db.execute(
        "INSERT INTO bias_logs (job_id, analysis_json, created_at) VALUES (?, ?, datetime('now'))",
        (job_id, json.dumps(report)),
    )
    db.commit()

    return report
