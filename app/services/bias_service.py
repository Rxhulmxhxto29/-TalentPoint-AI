"""
app/services/bias_service.py — Bias and fairness analysis for ranked candidates.

Analyzes ranking results for potential bias signals:
1. Experience-length skew (are high-YoE candidates always top-ranked?)
2. Factor dominance (does one scoring factor control rankings?)
3. Keyword overfit (are semantic scores very close to Jaccard scores?)

Important: This module surfaces signals for human review.
It does NOT make automated fairness decisions.
All reports include an ethical disclaimer.

References:
- Mehrabi et al. (2021) — A Survey on Bias and Fairness in Machine Learning
- EU AI Act (2024) — High-risk AI system transparency requirements
"""

import logging
import statistics
from datetime import datetime
from typing import Any, List

logger = logging.getLogger(__name__)

ETHICAL_DISCLAIMER = (
    "IMPORTANT: This bias analysis is a decision-support tool, not a fairness certification. "
    "Detected signals require human judgment. Correlation between scores and experience length "
    "does not necessarily indicate unfair bias — it may reflect legitimate job requirements. "
    "Resume screening AI can perpetuate historical biases present in training data and "
    "human-authored job descriptions. Final hiring decisions must always involve human oversight. "
    "Feature masking (removing experience signals) is available via the API for comparative testing."
)


def _compute_spearman_correlation(x: list[float], y: list[float]) -> float:
    """
    Compute Spearman rank correlation between two score lists.
    Returns value in [-1, 1]. +1 = perfect positive rank correlation.
    """
    if len(x) < 3 or len(x) != len(y):
        return 0.0

    def rank_list(lst: list[float]) -> list[float]:
        sorted_vals = sorted(enumerate(lst), key=lambda t: t[1], reverse=True)
        ranks = [0.0] * len(lst)
        for rank_pos, (orig_idx, _) in enumerate(sorted_vals, start=1):
            ranks[orig_idx] = float(rank_pos)
        return ranks

    rx = rank_list(x)
    ry = rank_list(y)
    n = len(x)
    d_sq_sum = sum((a - b) ** 2 for a, b in zip(rx, ry))
    if n <= 1:
        return 0.0
    rho = 1.0 - (6 * d_sq_sum) / (n * (n**2 - 1))
    # Manual round for IDE compatibility
    rounded_rho = float(int(float(rho) * 10000) / 10000.0)
    return float(rounded_rho)


def _detect_experience_skew(
    ranked_candidates: list[dict[str, Any]],
) -> tuple[float, list[int]]:
    """
    Detect if candidates with more YoE are systematically ranked higher.
    
    Returns:
        skew_score: 0=no skew, 1=perfect rank-YoE correlation
        affected_candidate_ids: resumes showing strong effect
    """
    if len(ranked_candidates) < 3:
        return 0.0, []

    total_scores = [c["total_score"] for c in ranked_candidates]
    yoe_values = [c.get("candidate_years_experience", 0.0) for c in ranked_candidates]

    rho = abs(_compute_spearman_correlation(total_scores, yoe_values))

    # Flag top-3 candidates whose YoE is notably high
    affected = []
    if rho > 0.6:
        avg_yoe = float(statistics.mean(yoe_values)) if yoe_values else 0.0
        # Use cast-like list conversion to ensure indexability
        ranked_list = list(ranked_candidates)
        # pyre-ignore[16]: Pyre fails to resolve list slice overload in this context
        top_candidates: List[dict[str, Any]] = ranked_list[0:3]
        for c in top_candidates:
            yoe = float(c.get("candidate_years_experience", 0.0))
            if yoe > avg_yoe * 1.5:
                affected.append(int(c["resume_id"]))

    rounded_rho = float(int(float(rho) * 10000) / 10000.0)
    return float(rounded_rho), affected


def _detect_keyword_overfit(
    ranked_candidates: list[dict[str, Any]],
) -> float:
    """
    Measure how closely the skill_match (Jaccard-based) score predicts total rank.
    High correlation = ranking is driven by keyword matching, not semantic understanding.
    
    Returns a score in [0, 1]: 0=semantic dominant, 1=keyword-driven.
    """
    if len(ranked_candidates) < 3:
        return 0.0

    total_scores = [c["total_score"] for c in ranked_candidates]
    skill_scores = [
        c["score_breakdown"].get("skill_match", 0.0)
        for c in ranked_candidates
    ]

    rho = abs(_compute_spearman_correlation(total_scores, skill_scores))
    # Manual round for IDE compatibility
    rounded_rho = float(int(float(rho) * 10000) / 10000.0)
    return float(rounded_rho)


def _compute_factor_dominance(
    ranked_candidates: list[dict[str, Any]],
    weights: dict[str, float],
) -> list[dict[str, Any]]:
    """
    Compute which factor contributes most to final scores, on average.
    
    Returns list of factor analysis dicts.
    """
    if not ranked_candidates:
        return []

    factor_keys = ["skill_match", "experience_alignment", "role_relevance"]
    dominance_results = []

    for factor in factor_keys:
        factor_weight = weights.get(factor, 0.33)
        raw_scores = [
            c["score_breakdown"].get(factor, 0.0) for c in ranked_candidates
        ]
        avg_raw = statistics.mean(raw_scores) if raw_scores else 0.0
        avg_contribution = avg_raw * factor_weight  # weighted contribution to total

        dominance_results.append({
            "factor_name": factor,
            "weight_used": float(int(float(factor_weight) * 1000) / 1000.0),
            "average_raw_score": float(int(float(avg_raw) * 10000) / 10000.0),
            "average_contribution": float(int(float(avg_contribution) * 10000) / 10000.0),
            "dominance_flag": bool(avg_contribution > 0.35),  # contributes >35% of max possible
        })

    return dominance_results


def _identify_bias_signals(
    experience_skew: float,
    keyword_overfit: float,
    factor_dominance: list[dict],
    skew_affected_ids: list[int],
) -> list[dict[str, Any]]:
    """Aggregate bias signals based on computed metrics."""
    signals = []

    # Experience skew signal
    if experience_skew > 0.7:
        signals.append({
            "signal_type": "experience_skew",
            "severity": "high",
            "description": (
                f"Strong correlation ({experience_skew:.2f}) between years of experience "
                f"and ranking. Candidates with fewer years may be unfairly penalized "
                f"even if their skills are a better match for this level."
            ),
            "affected_candidates": skew_affected_ids,
        })
    elif experience_skew > 0.45:
        signals.append({
            "signal_type": "experience_skew",
            "severity": "medium",
            "description": (
                f"Moderate experience-rank correlation ({experience_skew:.2f}). "
                f"Review whether experience requirements are truly necessary for this role."
            ),
            "affected_candidates": skew_affected_ids,
        })

    # Keyword overfit signal
    if keyword_overfit > 0.75:
        signals.append({
            "signal_type": "keyword_overfit",
            "severity": "high",
            "description": (
                f"Rankings closely mirror keyword presence (score: {keyword_overfit:.2f}). "
                f"Candidates with equivalent skills described differently may be underranked. "
                f"Consider increasing the role_relevance weight for semantic-first scoring."
            ),
            "affected_candidates": [],
        })
    elif keyword_overfit > 0.5:
        signals.append({
            "signal_type": "keyword_overfit",
            "severity": "medium",
            "description": (
                f"Moderate keyword influence on rankings ({keyword_overfit:.2f}). "
                f"Semantic similarity partially compensates, but check skill normalization."
            ),
            "affected_candidates": [],
        })

    # Factor dominance signal
    for factor in factor_dominance:
        if factor["dominance_flag"] and factor["weight_used"] > 0.45:
            signals.append({
                "signal_type": "factor_dominance",
                "severity": "medium",
                "description": (
                    f"Factor '{factor['factor_name']}' is heavily weighted ({factor['weight_used']:.0%}) "
                    f"and dominates rankings. Consider rebalancing weights via recruiter feedback."
                ),
                "affected_candidates": [],
            })

    return signals


def analyze_bias(
    ranked_candidates: list[dict[str, Any]],
    job_id: int,
    job_title: str,
    weights: dict[str, float],
) -> dict[str, Any]:
    """
    Generate a bias report for a set of ranked candidates.

    Returns a structured report dict matching BiasReport schema.
    """
    if not ranked_candidates:
        return {
            "job_id": job_id,
            "job_title": job_title,
            "total_candidates_analyzed": 0,
            "factor_dominance": [],
            "bias_signals": [],
            "experience_skew_score": 0.0,
            "keyword_overfit_score": 0.0,
            "ethical_disclaimer": ETHICAL_DISCLAIMER,
            "generated_at": datetime.utcnow().isoformat(),
        }

    experience_skew, skew_affected = _detect_experience_skew(ranked_candidates)
    keyword_overfit = _detect_keyword_overfit(ranked_candidates)
    factor_dominance = _compute_factor_dominance(ranked_candidates, weights)
    bias_signals = _identify_bias_signals(
        experience_skew, keyword_overfit, factor_dominance, skew_affected
    )

    logger.info(
        f"Bias analysis complete | job_id={job_id} | "
        f"exp_skew={experience_skew:.2f} | keyword_overfit={keyword_overfit:.2f} | "
        f"signals={len(bias_signals)}"
    )

    return {
        "job_id": job_id,
        "job_title": job_title,
        "total_candidates_analyzed": len(ranked_candidates),
        "factor_dominance": factor_dominance,
        "bias_signals": bias_signals,
        "experience_skew_score": experience_skew,
        "keyword_overfit_score": keyword_overfit,
        "ethical_disclaimer": ETHICAL_DISCLAIMER,
        "generated_at": datetime.utcnow().isoformat(),
    }
