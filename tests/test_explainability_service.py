"""
tests/test_explainability_service.py — Tests for explanation generation.
"""

import pytest  # type: ignore
from app.services.explainability_service import (  # type: ignore
    generate_explanation,
    generate_explanations_for_ranking,
    _describe_score_level,
    THRESHOLD_STRONG,
    THRESHOLD_WEAK,
)


class TestScoreDescriptor:
    def test_strong_threshold(self):
        assert _describe_score_level(THRESHOLD_STRONG) == "strong"
        assert _describe_score_level(1.0) == "strong"

    def test_weak_threshold(self):
        assert _describe_score_level(THRESHOLD_WEAK - 0.01) == "weak"

    def test_moderate_range(self):
        assert _describe_score_level(0.55) == "moderate"


class TestExplanationGeneration:
    def test_contains_rank(self):
        explanation = generate_explanation(
            rank=1,
            candidate_name="Priya Sharma",
            score_breakdown={"skill_match": 0.85, "experience_alignment": 0.90,
                             "role_relevance": 0.78, "total": 0.85},
            matched_skills=["Python", "NLP", "PyTorch"],
            missing_skills=[],
            candidate_yoe=7.0,
            min_required_yoe=5.0,
        )
        assert "#1" in explanation

    def test_contains_total_score(self):
        explanation = generate_explanation(
            rank=2, candidate_name="Anika",
            score_breakdown={"skill_match": 0.60, "experience_alignment": 0.70,
                             "role_relevance": 0.55, "total": 0.62},
            matched_skills=["Python"],
            missing_skills=["NLP"],
            candidate_yoe=4.0, min_required_yoe=5.0,
        )
        assert "0.62" in explanation

    def test_mentions_missing_skills(self):
        explanation = generate_explanation(
            rank=3, candidate_name="Rahul",
            score_breakdown={"skill_match": 0.20, "experience_alignment": 0.30,
                             "role_relevance": 0.40, "total": 0.29},
            matched_skills=["Python"],
            missing_skills=["NLP", "PyTorch", "Docker"],
            candidate_yoe=1.0, min_required_yoe=5.0,
        )
        assert "NLP" in explanation or "PyTorch" in explanation or "Docker" in explanation

    def test_mentions_matched_skills_for_strong(self):
        explanation = generate_explanation(
            rank=1, candidate_name="Vikram",
            score_breakdown={"skill_match": 0.90, "experience_alignment": 0.95,
                             "role_relevance": 0.88, "total": 0.91},
            matched_skills=["Python", "Machine Learning", "NLP", "Docker"],
            missing_skills=[],
            candidate_yoe=10.0, min_required_yoe=5.0,
        )
        # Should mention at least one matched skill
        assert any(s in explanation for s in ["Python", "Machine Learning", "NLP", "Docker"])

    def test_explanation_is_string(self):
        result = generate_explanation(
            rank=1, candidate_name="Test",
            score_breakdown={"skill_match": 0.5, "experience_alignment": 0.5,
                             "role_relevance": 0.5, "total": 0.5},
            matched_skills=[], missing_skills=[],
            candidate_yoe=3.0, min_required_yoe=2.0,
        )
        assert isinstance(result, str) and len(result) > 20


class TestBulkExplanation:
    def test_all_candidates_get_explanation(self, sample_ranked_candidates):
        result = generate_explanations_for_ranking(sample_ranked_candidates, min_required_yoe=5.0)
        for c in result:
            assert "explanation" in c
            assert isinstance(c["explanation"], str)
            assert len(c["explanation"]) > 10

    def test_explanations_mention_rank(self, sample_ranked_candidates):
        result = generate_explanations_for_ranking(sample_ranked_candidates, min_required_yoe=5.0)
        for c in result:
            assert f"#{c['rank']}" in c["explanation"]
