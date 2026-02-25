"""
app/services/explainability_service.py — Human-readable explanation generation.

For every ranked candidate, generates:
- Matched skills list
- Missing skills list
- Score breakdown (per factor)
- Natural language explanation (template-based, deterministic, no LLM)

Design principle:
Explanations must be understandable by non-technical recruiters.
They must be accurate (derived from actual scores) and consistent
(same inputs → same output — no randomness).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Strength / weakness thresholds for NL generation
# ---------------------------------------------------------------------------

THRESHOLD_STRONG = 0.70
THRESHOLD_MODERATE = 0.45
THRESHOLD_WEAK = 0.25


def _describe_score_level(score: float) -> str:
    """Convert a numeric score to a human-readable descriptor."""
    if score >= THRESHOLD_STRONG:
        return "strong"
    elif score >= THRESHOLD_MODERATE:
        return "moderate"
    elif score >= THRESHOLD_WEAK:
        return "limited"
    else:
        return "weak"


def _build_strength_sentence(
    skill_score: float,
    matched_skills: list[str],
    experience_score: float,
    candidate_yoe: float,
    role_relevance_score: float,
) -> str:
    """Generate the positive part of the explanation."""
    parts = []

    # Skill strength
    if skill_score >= THRESHOLD_MODERATE and matched_skills:
        matched_list = list(matched_skills)
        # pyre-ignore[16]: Pyre fails to resolve list slice overload
        top_skills = matched_list[0:4]  # cap at 4 for readability
        skills_str = ", ".join(top_skills)
        parts.append(
            f"{_describe_score_level(skill_score).capitalize()} skill alignment "
            f"with {skills_str}"
        )

    # Experience strength
    if experience_score >= THRESHOLD_STRONG:
        parts.append(
            f"well-matched experience ({candidate_yoe:.0f} yrs)"
        )
    elif experience_score >= THRESHOLD_MODERATE:
        parts.append(f"adequate experience ({candidate_yoe:.0f} yrs)")

    # Role relevance strength
    if role_relevance_score >= THRESHOLD_STRONG:
        parts.append("strong semantic alignment with role requirements")
    elif role_relevance_score >= THRESHOLD_MODERATE:
        parts.append("moderate role-level fit")

    if not parts:
        return "Limited alignment with this role. "
    return ", ".join(parts) + ". "


def _build_weakness_sentence(
    missing_skills: list[str],
    experience_score: float,
    candidate_yoe: float,
    min_required_yoe: float,
) -> str:
    """Generate the constructive-criticism part of the explanation."""
    weaknesses = []

    if missing_skills:
        missing_list = list(missing_skills)
        # pyre-ignore[16]: Pyre fails to resolve list slice overload
        top_missing = missing_list[0:3]
        missing_str = ", ".join(top_missing)
        remainder = len(missing_skills) - len(top_missing)
        suffix = f" (+{remainder} more)" if remainder > 0 else ""
        weaknesses.append(f"lacks required skills: {missing_str}{suffix}")

    if experience_score < THRESHOLD_MODERATE and candidate_yoe < min_required_yoe:
        diff = float(min_required_yoe - candidate_yoe)
        shortfall = float(int(diff * 10) / 10.0)
        weaknesses.append(f"under-qualified by ~{shortfall} yrs experience")

    if not weaknesses:
        return ""

    return "However, " + "; ".join(weaknesses) + ". "


def generate_explanation(
    rank: int,
    candidate_name: str,
    score_breakdown: dict[str, float],
    matched_skills: list[str],
    missing_skills: list[str],
    candidate_yoe: float,
    min_required_yoe: float,
) -> str:
    """
    Generate a recruiter-facing natural language explanation for a ranked candidate.

    Args:
        rank: Candidate's rank (1 = best)
        candidate_name: Candidate's name
        score_breakdown: {skill_match, experience_alignment, role_relevance, total}
        matched_skills: Skills found in both resume and JD
        missing_skills: Required skills absent from resume
        candidate_yoe: Candidate years of experience
        min_required_yoe: Job's minimum years required

    Returns:
        String explanation for non-technical recruiter.
    """
    skill_score = score_breakdown.get("skill_match", 0.0)
    exp_score = score_breakdown.get("experience_alignment", 0.0)
    relevance_score = score_breakdown.get("role_relevance", 0.0)
    total_score = score_breakdown.get("total", 0.0)

    rank_label = f"#{rank}"
    preamble = (
        f"Ranked {rank_label} overall (score: {total_score:.2f}/1.00). "
    )
    strength = _build_strength_sentence(
        skill_score, matched_skills, exp_score, candidate_yoe, relevance_score
    )
    weakness = _build_weakness_sentence(
        missing_skills, exp_score, candidate_yoe, min_required_yoe
    )

    # Professional Insight: Skill over Tenure
    insight = ""
    if relevance_score > 0.85 and skill_score > 0.85 and exp_score < 0.6:
        insight = " **[High Potential: Strong skill signals outweigh raw tenure.]**"
    elif exp_score < 0.3 and total_score > 0.6:
        insight = " **[Note: Profile suggests likely seniority not explicitly captured in dates.]**"

    score_summary = (
        f"[Skill: {skill_score:.2f} | Experience: {exp_score:.2f} | "
        f"Role Fit: {relevance_score:.2f}]"
    )

    explanation = preamble + strength + weakness + insight + score_summary
    explanation_str = str(explanation)
    # pyre-ignore[16]: Pyre fails to resolve str slice overload
    logger.debug(f"Generated explanation for rank={rank}: {explanation_str[0:80]}...")
    return explanation


def generate_explanations_for_ranking(
    ranked_candidates: list[dict[str, Any]],
    min_required_yoe: float = 0.0,
) -> list[dict[str, Any]]:
    """
    Add explanations to all ranked candidates in-place.
    Called after ranking_service.rank_candidates().

    Returns the same list with 'explanation' key populated on each entry.
    """
    for candidate in ranked_candidates:
        candidate["explanation"] = generate_explanation(
            rank=candidate["rank"],
            candidate_name=candidate.get("candidate_name", "Unknown"),
            score_breakdown=candidate["score_breakdown"],
            matched_skills=candidate.get("matched_skills", []),
            missing_skills=candidate.get("missing_skills", []),
            candidate_yoe=candidate.get("candidate_years_experience", 0.0),
            min_required_yoe=min_required_yoe,
        )
    return ranked_candidates
