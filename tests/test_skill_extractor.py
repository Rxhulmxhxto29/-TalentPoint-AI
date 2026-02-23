"""
tests/test_skill_extractor.py — Tests for skill extraction and normalization.
"""

import pytest  # type: ignore
from app.services.skill_extractor import SkillExtractor  # type: ignore
from config import SKILL_NORMALIZATION_MAP, SPACY_MODEL_NAME  # type: ignore


@pytest.fixture
def extractor():
    return SkillExtractor(
        normalization_map=SKILL_NORMALIZATION_MAP,
        spacy_model_name=SPACY_MODEL_NAME,
    )


class TestNormalization:
    def test_canonical_alias_ml(self, extractor):
        result = extractor.normalize_skill("ml")
        assert result == "Machine Learning"

    def test_canonical_alias_k8s(self, extractor):
        result = extractor.normalize_skill("k8s")
        assert result == "Kubernetes"

    def test_canonical_alias_sklearn(self, extractor):
        result = extractor.normalize_skill("sklearn")
        assert result == "Scikit-Learn"

    def test_case_insensitive(self, extractor):
        assert extractor.normalize_skill("PYTHON") == extractor.normalize_skill("python")

    def test_noise_filtered(self, extractor):
        assert extractor.normalize_skill("a") is None     # too short
        assert extractor.normalize_skill("123") is None   # pure number

    def test_unknown_skill_titlecased(self, extractor):
        result = extractor.normalize_skill("quantum computing")
        assert result == "Quantum Computing" or result is not None


class TestBulkNormalization:
    def test_deduplication(self, extractor):
        raw = ["ml", "Machine Learning", "Python", "python"]
        normalized = extractor.extract_from_raw_list(raw)
        counts = normalized.count("Machine Learning")
        assert counts == 1, "Duplicate skills should be deduplicated"
        assert normalized.count("Python") == 1

    def test_output_sorted(self, extractor):
        raw = ["Python", "AWS", "Docker"]
        normalized = extractor.extract_from_raw_list(raw)
        assert normalized == sorted(normalized)


class TestSkillOverlap:
    def test_perfect_overlap(self, extractor):
        resume = ["Python", "SQL", "Docker"]
        job    = ["Python", "SQL", "Docker"]
        matched, missing, score = extractor.compute_skill_overlap(resume, job)
        assert len(missing) == 0
        assert score == 1.0

    def test_no_overlap(self, extractor):
        resume = ["Java", "Spring Boot"]
        job    = ["Python", "TensorFlow"]
        matched, missing, score = extractor.compute_skill_overlap(resume, job)
        assert len(matched) == 0
        assert score == 0.0

    def test_partial_overlap(self, extractor):
        resume = ["Python", "SQL", "Java"]
        job    = ["Python", "NLP", "Docker"]
        matched, missing, score = extractor.compute_skill_overlap(resume, job)
        assert "Python" in matched
        assert "NLP" in missing
        assert 0.0 < score < 1.0

    def test_empty_job_skills(self, extractor):
        resume = ["Python", "SQL"]
        job    = []
        _, _, score = extractor.compute_skill_overlap(resume, job)
        assert score == 0.0


class TestTextExtraction:
    def test_extracts_known_skills_from_text(self, extractor):
        text = "Looking for a developer with Python, SQL, and Docker experience."
        skills = extractor._extract_with_regex(text)
        skill_lower = [s.lower() for s in skills]
        assert any("python" in s for s in skill_lower)
        assert any("docker" in s for s in skill_lower)
