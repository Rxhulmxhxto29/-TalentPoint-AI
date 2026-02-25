"""
app/services/ranking_service.py — Multi-factor candidate ranking.

Scoring Pipeline (per candidate):
1. Skill Match Score    (weight: configurable, default 0.40)
   - Jaccard overlap of canonical skills
   - Boosted by embedding similarity of skill set texts

2. Experience Alignment Score  (weight: 0.30)
   - Normalized distance between candidate YoE and job requirement
   - Penalizes both under- and over-qualification (with asymmetry)

3. Role Relevance Score  (weight: 0.30)
   - Cosine similarity between full resume embedding and JD embedding

Total Score = w1*skill + w2*experience + w3*relevance

All scores are in [0, 1]. Weights sum to 1.0.
"""


# pyre-ignore[21]: Pyre fails to resolve numpy in this context
import numpy as np
import logging
import math
from pathlib import Path
from typing import Any, List, Optional, Dict

logger = logging.getLogger(__name__)


def _compute_skill_match_score(
    resume_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    embedding_service,
) -> tuple[float, list[str], list[str]]:
    """
    Compute skill match score combining Jaccard similarity and embedding boost.

    Returns:
        score (float in [0,1])
        matched_skills (list)
        missing_skills (list — required skills not in resume)
    """
    # pyre-ignore[21]: Pyre fails to resolve internal import
    from app.services.skill_extractor import get_skill_extractor
    extractor = get_skill_extractor()

    # Jaccard over required skills (primary)
    matched_req, missing_req, jaccard_req = extractor.compute_skill_overlap(
        resume_skills, required_skills
    )

    # Jaccard over preferred skills (secondary, lower weight)
    _, _, jaccard_pref = extractor.compute_skill_overlap(
        resume_skills, preferred_skills
    ) if preferred_skills else ([], [], 0.0)

    # Combined Jaccard (required skills count more)
    if required_skills:
        skill_jaccard = 0.75 * jaccard_req + 0.25 * jaccard_pref
    else:
        skill_jaccard = jaccard_pref  # fallback if no required skills

    # Embedding boost: semantic similarity of skill set texts
    # This captures synonymous skills the Jaccard misses
    embedding_boost = 0.0
    if embedding_service is not None and resume_skills and (required_skills or preferred_skills):
        try:
            resume_skill_text = ", ".join(resume_skills)
            job_skill_text = ", ".join(required_skills + preferred_skills)
            resume_emb = embedding_service.encode([resume_skill_text])
            job_emb = embedding_service.encode([job_skill_text])
            embedding_boost = embedding_service.cosine_similarity(resume_emb[0], job_emb[0])
        except Exception as e:
            logger.warning(f"Embedding boost computation failed: {e}")

    # Final skill score: blend Jaccard and embedding similarity
    skill_score = 0.60 * skill_jaccard + 0.40 * embedding_boost

    return float(min(1.0, max(0.0, skill_score))), matched_req, missing_req


def _compute_experience_alignment_score(
    candidate_years: float,
    min_required_years: float,
    max_required_years: float | None,
) -> float:
    """
    Score how well the candidate's experience aligns with the job requirement.

    Logic:
    - Below minimum: linearly penalized (under-qualified)
    - Within range: score 1.0
    - Above max: slightly penalized (over-qualified, less severe)
    """
    if min_required_years == 0.0 and not max_required_years:
        # Job has no experience requirement — everyone scores equally
        return 0.75  # neutral score, not 1.0 to avoid false precision

    effective_max = max_required_years if max_required_years else min_required_years + 5.0

    if candidate_years < min_required_years:
        # Under-qualified penalty: proportional to shortfall
        shortfall = min_required_years - candidate_years
        penalty = min(1.0, shortfall / max(1.0, min_required_years))
        return float(max(0.0, 1.0 - penalty))

    elif candidate_years <= effective_max:
        # Within range — perfect score
        return 1.0

    else:
        # Over-qualified — mild penalty
        surplus = candidate_years - effective_max
        penalty = min(0.3, surplus * 0.04)  # max 30% penalty for over-qualification
        return float(max(0.7, 1.0 - penalty))


def _compute_role_relevance_score(
    resume_text: str,
    jd_text: str,
    embedding_service,
) -> float:
    """
    Semantic similarity between the full resume text and job description.
    Uses pre-computed or freshly computed BERT embeddings.
    """
    if embedding_service is None:
        logger.warning("Embedding service unavailable — falling back to 0.5 relevance")
        return 0.5  # neutral fallback

    try:
        text_str = str(resume_text)
        jd_str = str(jd_text)
        # pyre-ignore[16]: Pyre fails to resolve str slice overload
        resume_emb = embedding_service.get_resume_embedding(text_str[0:4000])
        # pyre-ignore[16]: Pyre fails to resolve str slice overload
        jd_emb = embedding_service.get_jd_embedding(jd_str[0:2000])
        return float(embedding_service.cosine_similarity(resume_emb, jd_emb))
    except Exception as e:
        logger.error(f"Role relevance scoring failed: {e}")
        return 0.5


def _compute_total_score(
    skill_score: float,
    experience_score: float,
    role_relevance_score: float,
    weights: dict[str, float],
) -> float:
    """Weighted sum of all factor scores."""
    total = (
        weights["skill_match"] * skill_score
        + weights["experience_alignment"] * experience_score
        + weights["role_relevance"] * role_relevance_score
    )
    val = float(min(1.0, max(0.0, total)))
    return float(int(val * 10000) / 10000.0)


def rank_candidates(
    parsed_resumes: list[dict[str, Any]],
    parsed_job: dict[str, Any],
    weights: dict[str, float],
    embedding_service,
    skills_first: bool = False,
) -> list[dict[str, Any]]:
    """
    Main ranking function.

    Args:
        parsed_resumes: List of dicts from resume_parser (with id, parsed fields)
        parsed_job: Dict from jd_parser
        weights: Scoring weights dict {skill_match, experience_alignment, role_relevance}
        embedding_service: EmbeddingService instance (or None for degraded mode)

    Returns:
        Sorted list of candidate score dicts, rank 1 = best match.
    """
    required_skills = parsed_job.get("required_skills", [])
    preferred_skills = parsed_job.get("preferred_skills", [])
    min_yoe = parsed_job.get("min_years_experience", 0.0)
    max_yoe = parsed_job.get("max_years_experience", None)
    jd_text = parsed_job.get("raw_text", "")

    scored_candidates: list[dict[str, Any]] = []

    for resume in parsed_resumes:
        resume_id = resume["id"]
        parsed = resume["parsed"]

        try:
            # Factor 1: Skill Match
            skill_score, matched, missing = _compute_skill_match_score(
                resume_skills=parsed.get("skills", []),
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                embedding_service=embedding_service,
            )

            # Factor 2: Experience Alignment
            exp_score = _compute_experience_alignment_score(
                candidate_years=parsed.get("total_years_experience", 0.0),
                min_required_years=min_yoe,
                max_required_years=max_yoe,
            )

            # Factor 3: Role Relevance
            relevance_score = _compute_role_relevance_score(
                resume_text=parsed.get("raw_text", ""),
                jd_text=jd_text,
                embedding_service=embedding_service,
            )

            total = _compute_total_score(
                skill_score, exp_score, relevance_score, weights
            )

            # --- Talent Boost (Professional Heuristic) ---
            # If skills_first is ON, we drastically dampen the YoE penalty.
            # Otherwise, we use the "High Potential" heuristic (Skills > 85% + Relevance > 85%).
            is_high_potential = bool(relevance_score > 0.85 and skill_score > 0.85)
            boost_applied = False
            
            if skills_first and exp_score < 0.8:
                boost = (1.0 - exp_score) * 0.6  # drastically dampen seniority bias
                total = min(1.0, total + (boost * weights["experience_alignment"]))
                boost_applied = True
            elif is_high_potential and exp_score < 0.6:
                boost = (1.0 - exp_score) * 0.4  # moderate boost for exceptional talent
                total = min(1.0, total + (boost * weights["experience_alignment"]))
                boost_applied = True

            score_breakdown = {
                "skill_match": float(int(float(skill_score) * 10000) / 10000.0),
                "experience_alignment": float(int(float(exp_score) * 10000) / 10000.0),
                "role_relevance": float(int(float(relevance_score) * 10000) / 10000.0),
                "total": float(total),
                "boost_applied": boost_applied
            }

            scored_candidates.append({
                "resume_id": resume_id,
                "candidate_name": parsed.get("name", f"Candidate {resume_id}"),
                "total_score": total,
                "score_breakdown": score_breakdown,
                "matched_skills": matched,
                "missing_skills": missing,
                "candidate_years_experience": parsed.get("total_years_experience", 0.0),
                "high_potential": boost_applied,
            })

        except Exception as e:
            logger.error(f"Scoring failed for resume_id={resume_id}: {e}", exc_info=True)

    # Sort by total score descending; break ties by skill_match
    scored_candidates.sort(
        key=lambda x: (x["total_score"], x["score_breakdown"]["skill_match"]),
        reverse=True,
    )

    # Assign rank (1-indexed, 1 = best)
    for rank_idx, candidate in enumerate(scored_candidates, start=1):
        candidate["rank"] = rank_idx

    logger.info(
        f"Ranked {len(scored_candidates)} candidates | "
        f"top_score={scored_candidates[0]['total_score'] if scored_candidates else 'N/A'}"
    )

    return scored_candidates
