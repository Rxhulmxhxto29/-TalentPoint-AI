"""
app/schemas/models.py — Pydantic v2 typed schemas for all request/response objects.

These schemas enforce contract at the API boundary.
All ML services return plain dicts internally; routers convert to these schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator  # type: ignore


# ==============================================================================
# Resume Schemas
# ==============================================================================

class ParsedResume(BaseModel):
    """Structured output from resume parsing pipeline."""
    name: str = Field(description="Candidate's full name (extracted or filename fallback)")
    skills: list[str] = Field(default_factory=list, description="Normalized canonical skills")
    experience_entries: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of experience blocks: {title, company, duration_years, description}"
    )
    total_years_experience: float = Field(
        default=0.0, description="Estimated total years of professional experience"
    )
    education: list[dict[str, str]] = Field(
        default_factory=list,
        description="Education blocks: {degree, institution, year}"
    )
    summary: str = Field(default="", description="Professional summary or objective section")
    raw_text: str = Field(description="Full extracted text before parsing")


class ResumeRecord(BaseModel):
    """A resume as stored in the database."""
    id: int
    name: str
    file_name: Optional[str] = None
    parsed: ParsedResume
    created_at: datetime


class ResumeListItem(BaseModel):
    """Lightweight resume entry for listing endpoints."""
    id: int
    name: str
    file_name: Optional[str] = None
    total_years_experience: float
    skill_count: int
    created_at: datetime


# ==============================================================================
# Job Description Schemas
# ==============================================================================

class ParsedJob(BaseModel):
    """Structured output from job description parsing pipeline."""
    title: str = Field(description="Job title")
    required_skills: list[str] = Field(
        default_factory=list, description="Skills explicitly required"
    )
    preferred_skills: list[str] = Field(
        default_factory=list, description="Skills that are nice-to-have"
    )
    min_years_experience: float = Field(
        default=0.0, description="Minimum years of experience required"
    )
    max_years_experience: Optional[float] = Field(
        default=None, description="Maximum years (for leveling)"
    )
    role_context: str = Field(
        default="", description="Domain/context summary of the role"
    )
    raw_text: str = Field(description="Original job description text")


class JobCreate(BaseModel):
    """Request schema for creating a new job description."""
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=50, description="Full job description text")


class JobRecord(BaseModel):
    """A job as stored in the database."""
    id: int
    title: str
    parsed: ParsedJob
    weights: ScoringWeights
    created_at: datetime


class JobListItem(BaseModel):
    """Lightweight job entry for listing endpoints."""
    id: int
    title: str
    required_skill_count: int
    min_years_experience: float
    created_at: datetime


# ==============================================================================
# Scoring & Ranking Schemas
# ==============================================================================

class ScoringWeights(BaseModel):
    """
    Configurable weights for multi-factor ranking.
    Must sum to 1.0 (validated).
    """
    skill_match: float = Field(default=0.40, ge=0.10, le=0.70)
    experience_alignment: float = Field(default=0.30, ge=0.10, le=0.70)
    role_relevance: float = Field(default=0.30, ge=0.10, le=0.70)

    @field_validator("role_relevance")
    @classmethod
    def weights_must_sum_to_one(cls, v: float, info: Any) -> float:
        data = info.data
        if "skill_match" in data and "experience_alignment" in data:
            total = data["skill_match"] + data["experience_alignment"] + v
            if not (0.98 <= total <= 1.02):  # allow float tolerance
                raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")
        return v


class ScoreBreakdown(BaseModel):
    """Per-factor score breakdown for a single candidate."""
    skill_match: float = Field(ge=0.0, le=1.0)
    experience_alignment: float = Field(ge=0.0, le=1.0)
    role_relevance: float = Field(ge=0.0, le=1.0)
    total: float = Field(ge=0.0, le=1.0)


class RankedCandidate(BaseModel):
    """A single candidate entry in a ranked result set."""
    rank: int
    resume_id: int
    candidate_name: str
    total_score: float = Field(ge=0.0, le=1.0)
    score_breakdown: ScoreBreakdown
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: str = Field(description="Human-readable NL explanation for recruiter")


class RankingResponse(BaseModel):
    """Full response from a ranking request."""
    job_id: int
    job_title: str
    candidate_count: int
    weights_used: ScoringWeights
    ranked_candidates: list[RankedCandidate]
    generated_at: datetime


# ==============================================================================
# Feedback Schemas
# ==============================================================================

class FeedbackCreate(BaseModel):
    """Recruiter feedback submission."""
    ranking_id: int
    decision: str = Field(description="'accept' or 'reject'")
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("decision")
    @classmethod
    def decision_must_be_valid(cls, v: str) -> str:
        if v not in ("accept", "reject"):
            raise ValueError("decision must be 'accept' or 'reject'")
        return v


class FeedbackRecord(BaseModel):
    id: int
    ranking_id: int
    job_id: int
    resume_id: int
    decision: str
    notes: Optional[str]
    created_at: datetime


class FeedbackStats(BaseModel):
    total_feedback: int
    accept_count: int
    reject_count: int
    acceptance_rate: float
    feedback_by_job: list[dict[str, Any]]
    weight_adjustments_triggered: int


# ==============================================================================
# Bias Analysis Schemas
# ==============================================================================

class FactorDominance(BaseModel):
    """Which scoring factor dominates across ranked candidates."""
    factor_name: str
    average_contribution: float     # weighted contribution to total score
    dominance_flag: bool            # True if this factor contributes > 50% of total


class BiasSignal(BaseModel):
    """A single potential bias signal detected in rankings."""
    signal_type: str    # e.g., "experience_skew", "keyword_overfit", "factor_dominance"
    severity: str       # "low" | "medium" | "high"
    description: str
    affected_candidates: list[int]  # resume_ids


class BiasReport(BaseModel):
    """Full bias analysis report for a job's ranked results."""
    job_id: int
    job_title: str
    total_candidates_analyzed: int
    factor_dominance: list[FactorDominance]
    bias_signals: list[BiasSignal]
    experience_skew_score: float = Field(
        ge=0.0, le=1.0,
        description="0=no skew, 1=high skew (high-YoE always ranked top)"
    )
    keyword_overfit_score: float = Field(
        ge=0.0, le=1.0,
        description="0=semantic understanding, 1=pure keyword matching"
    )
    ethical_disclaimer: str
    generated_at: datetime
