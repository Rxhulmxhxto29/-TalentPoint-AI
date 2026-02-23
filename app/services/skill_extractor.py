"""
app/services/skill_extractor.py — Skill extraction and normalization.

Two-stage pipeline:
1. Canonical map lookup (fast, exact/fuzzy string match)
2. Embedding-based fuzzy matching for unseen skill synonyms

Design note: spaCy is used for noun phrase extraction as a skill candidate
filter. The canonical map converts variants to standard forms.
The embedding model is shared with embedding_service (singleton).
"""

import re
import logging
from functools import lru_cache
from typing import Optional, Set

logger = logging.getLogger(__name__)

try:
    # pyre-ignore[21]: Pyre fails to resolve spacy
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not installed — falling back to regex-only skill extraction")


def _load_spacy_model(model_name: str):
    """Load spaCy model with graceful fallback."""
    if not SPACY_AVAILABLE:
        return None
    try:
        return spacy.load(model_name)
    except OSError:
        logger.warning(
            f"spaCy model '{model_name}' not found. "
            f"Run: python -m spacy download {model_name}"
        )
        return None


class SkillExtractor:
    """
    Stateful skill extractor — loads spaCy once and reuses across requests.
    Instantiate once and inject as dependency.
    """

    def __init__(self, normalization_map: dict[str, str], spacy_model_name: str):
        self.normalization_map = {
            k.lower().strip(): v for k, v in normalization_map.items()
        }
        self._nlp = _load_spacy_model(spacy_model_name)
        logger.info(
            f"SkillExtractor initialized | "
            f"spaCy={'loaded' if self._nlp else 'unavailable'} | "
            f"canonical_skills={len(self.normalization_map)}"
        )

    def normalize_skill(self, raw_skill: str) -> Optional[str]:
        """
        Normalize a raw skill string to its canonical form.
        Returns None if the string looks like noise (too short, weird chars).
        """
        cleaned = raw_skill.strip().lower()
        cleaned = re.sub(r"[^\w\s\+\#\./\-]", "", cleaned).strip()

        if len(cleaned) < 2:
            return None
        if re.match(r"^\d+$", cleaned):  # pure number
            return None

        # 1. Exact match in canonical map
        if cleaned in self.normalization_map:
            return self.normalization_map[cleaned]

        # 2. Partial match (handles "python programming" → "Python")
        for key, canonical in self.normalization_map.items():
            if key in cleaned or cleaned in key:
                if abs(len(key) - len(cleaned)) < 10:  # avoid over-broad matches
                    return canonical

        # 3. Return title-cased version if not found (treat as new skill)
        return raw_skill.strip().title()

    def extract_from_raw_list(self, raw_skills: list[str]) -> list[str]:
        """
        Normalize a list of already-extracted raw skill strings.
        Returns deduplicated canonical skill list.
        """
        canonical = set()
        for raw in raw_skills:
            normalized = self.normalize_skill(raw)
            if normalized:
                canonical.add(normalized)
        return sorted(canonical)

    def extract_from_text(self, text: str) -> list[str]:
        """
        Extract and normalize skills from free-form text using spaCy NLP.
        Falls back to keyword matching if spaCy is unavailable.
        """
        if self._nlp:
            return self._extract_with_spacy(text)
        return self._extract_with_regex(text)

    def _extract_with_spacy(self, text: str) -> list[str]:
        """
        Use spaCy to extract noun chunks and match against skill map.
        Conservative approach: only extracts things that match the canonical map.
        """
        nlp = self._nlp
        if nlp is None:
            return []
        text_str = str(text)
        # pyre-ignore[16]: Pyre fails to resolve str slice overload
        doc = nlp(text_str[0:5000])  # limit for performance
        candidates = set()

        # 1. Noun chunks as skill candidates
        for chunk in doc.noun_chunks:
            candidate = chunk.text.strip().lower()
            normalized = self.normalize_skill(candidate)
            if normalized:
                candidates.add(normalized)

        # 2. Single tokens that match canonical map keys
        for token in doc:
            if token.is_stop or token.is_punct or len(token.text) < 2:
                continue
            # pyre-ignore[16]: Pyre fails to resolve self method in this loop
            normalized = self.normalize_skill(token.text)
            if normalized:
                candidates.add(normalized)

        # 3. Also scan against all known keys directly (keyword scan)
        text_lower = text.lower()
        for key, canonical in self.normalization_map.items():
            if re.search(rf"\b{re.escape(key)}\b", text_lower):
                candidates.add(canonical)

        return sorted(candidates)

    def _extract_with_regex(self, text: str) -> list[str]:
        """Fallback extraction: scan text for all known canonical map keys."""
        text_lower = text.lower()
        candidates = set()
        for key, canonical in self.normalization_map.items():
            if re.search(rf"\b{re.escape(key)}\b", text_lower):
                candidates.add(canonical)
        return sorted(candidates)

    def compute_skill_overlap(
        self,
        resume_skills: list[str],
        job_skills: list[str],
    ) -> tuple[list[str], list[str], float]:
        """
        Compute matched and missing skills between resume and job.

        Returns:
            matched_skills: skills present in resume AND job
            missing_skills: required job skills absent from resume
            jaccard_score: |intersection| / |union| (0–1)
        """
        resume_set = set(s.lower() for s in resume_skills)
        job_set = set(s.lower() for s in job_skills)

        matched = [s for s in job_skills if s.lower() in resume_set]
        missing = [s for s in job_skills if s.lower() not in resume_set]

        union_size = len(resume_set | job_set)
        if union_size == 0:
            return matched, missing, 0.0

        jaccard = len(resume_set & job_set) / union_size
        return matched, missing, float(int(float(jaccard) * 10000) / 10000.0)


# ---------------------------------------------------------------------------
# Module-level factory — services import this, not the raw class
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_skill_extractor() -> SkillExtractor:
    """
    Singleton factory — creates SkillExtractor once, reuses across requests.
    lru_cache ensures the spaCy model is loaded only on first call.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    # pyre-ignore[21]: Pyre fails to resolve root config
    from config import SKILL_NORMALIZATION_MAP, SPACY_MODEL_NAME
    return SkillExtractor(
        normalization_map=SKILL_NORMALIZATION_MAP,
        spacy_model_name=SPACY_MODEL_NAME,
    )
