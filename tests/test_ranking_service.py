"""
tests/test_ranking_service.py — Tests for multi-factor ranking pipeline.
"""

import pytest  # type: ignore
from app.services.ranking_service import (  # type: ignore
    _compute_experience_alignment_score,
    _compute_total_score,
    rank_candidates,
)


class TestExperienceAlignment:
    def test_within_range_perfect_score(self):
        score = _compute_experience_alignment_score(6.0, 5.0, 8.0)
        assert score == 1.0

    def test_under_qualified_penalty(self):
        score = _compute_experience_alignment_score(1.0, 5.0, 8.0)
        assert score < 0.5, "Under-qualified candidate should be heavily penalized"

    def test_zero_requirement_neutral_score(self):
        score = _compute_experience_alignment_score(2.0, 0.0, None)
        assert score == 0.75, "No experience requirement → neutral 0.75"

    def test_over_qualified_mild_penalty(self):
        exact = _compute_experience_alignment_score(7.0, 5.0, 8.0)
        over  = _compute_experience_alignment_score(15.0, 5.0, 8.0)
        assert over < exact, "Over-qualified should score slightly less than in-range"
        assert over >= 0.70, "Over-qualification penalty should be mild (max 30%)"

    def test_slight_under_qualification(self):
        score = _compute_experience_alignment_score(4.5, 5.0, 8.0)
        assert score > 0.80, "Slightly under (0.5yr) should not heavily penalize"


class TestTotalScore:
    def test_weighted_sum_correct(self):
        weights = {"skill_match": 0.40, "experience_alignment": 0.30, "role_relevance": 0.30}
        total = _compute_total_score(0.80, 0.90, 0.70, weights)
        expected = 0.40*0.80 + 0.30*0.90 + 0.30*0.70
        assert abs(total - expected) < 1e-4

    def test_bounded_zero_to_one(self):
        weights = {"skill_match": 0.40, "experience_alignment": 0.30, "role_relevance": 0.30}
        total = _compute_total_score(1.0, 1.0, 1.0, weights)
        assert 0.0 <= total <= 1.0

    def test_zero_scores(self):
        weights = {"skill_match": 0.40, "experience_alignment": 0.30, "role_relevance": 0.30}
        total = _compute_total_score(0.0, 0.0, 0.0, weights)
        assert total == 0.0


class TestRankCandidateOrdering:
    def test_senior_ranks_above_junior(self):
        """Senior (7 YoE, strong skills) should rank above junior for 5+ YoE ML role."""
        resumes = [
            {
                "id": 1,
                "name": "Junior",
                "parsed": {
                    "name": "Junior Dev",
                    "skills": ["Python", "SQL"],
                    "total_years_experience": 1.0,
                    "raw_text": "Python SQL data analyst junior",
                },
            },
            {
                "id": 2,
                "name": "Senior",
                "parsed": {
                    "name": "Senior Dev",
                    "skills": ["Python", "Machine Learning", "NLP", "Docker", "PyTorch"],
                    "total_years_experience": 7.0,
                    "raw_text": "Senior ML Engineer Python Machine Learning NLP PyTorch Docker production AI",
                },
            },
        ]
        job = {
            "required_skills": ["Python", "Machine Learning", "NLP"],
            "preferred_skills": ["Docker", "PyTorch"],
            "min_years_experience": 5.0,
            "max_years_experience": None,
            "raw_text": "Senior ML Engineer 5 years Machine Learning NLP Python Docker",
        }
        weights = {"skill_match": 0.40, "experience_alignment": 0.30, "role_relevance": 0.30}
        ranked = rank_candidates(resumes, job, weights, embedding_service=None)

        assert ranked[0]["resume_id"] == 2, "Senior should be ranked #1"
        assert ranked[1]["resume_id"] == 1, "Junior should be ranked #2"

    def test_ranks_are_sequential(self):
        resumes = [
            {"id": i, "name": f"C{i}", "parsed": {
                "name": f"Candidate {i}",
                "skills": ["Python"],
                "total_years_experience": float(i),
                "raw_text": f"Candidate {i} Python developer",
            }}
            for i in range(1, 5)
        ]
        job = {
            "required_skills": ["Python"],
            "preferred_skills": [],
            "min_years_experience": 2.0,
            "max_years_experience": None,
            "raw_text": "Python developer 2 years",
        }
        ranked = rank_candidates(
            resumes, job, {"skill_match": 0.4, "experience_alignment": 0.3, "role_relevance": 0.3},
            embedding_service=None,
        )
        ranks = [c["rank"] for c in ranked]
        assert ranks == list(range(1, len(ranked) + 1)), "Ranks must be sequential starting at 1"

    def test_empty_resumes(self):
        job = {"required_skills": [], "preferred_skills": [],
               "min_years_experience": 0.0, "max_years_experience": None, "raw_text": ""}
        result = rank_candidates([], job, {"skill_match": 0.4, "experience_alignment": 0.3,
                                           "role_relevance": 0.3}, embedding_service=None)
        assert result == []
