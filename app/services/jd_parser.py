"""
app/services/jd_parser.py — Job description parsing and weight assignment.

Extracts structured requirements from a job description text:
- Required skills
- Preferred/nice-to-have skills
- Experience requirements
- Role context for semantic matching

Design: Rule-based extraction with spaCy assist.
Weight assignment is deterministic and configurable — not learned.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section patterns for JD structure
# ---------------------------------------------------------------------------

REQUIRED_SECTION_PATTERNS = re.compile(
    r"(required|must\s+have|mandatory|essential|minimum\s+qualifications?|"
    r"we\s+require|you\s+will\s+need|what\s+you(?:'ll)?\s+bring)",
    re.IGNORECASE,
)

PREFERRED_SECTION_PATTERNS = re.compile(
    r"(preferred|nice\s+to\s+have|bonus|good\s+to\s+have|plus|"
    r"desired?|advantage|optional)",
    re.IGNORECASE,
)

EXPERIENCE_PATTERNS = [
    # "5+ years of experience", "3-5 years", "minimum 2 years"
    re.compile(
        r"(\d+)\+?\s*(?:to|-)\s*(\d+)\s*years?\s+(?:of\s+)?(?:professional\s+)?experience",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:minimum\s+|at\s+least\s+)?(\d+)\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?experience",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:work(?:ing)?\s+)?experience",
        re.IGNORECASE,
    ),
    # New: "6 months experience", "3-6 months"
    re.compile(
        r"(\d+)\+?\s*(?:to|-)\s*(\d+)\s*months?\s+(?:of\s+)?(?:professional\s+)?experience",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:minimum\s+|at\s+least\s+)?(\d+)\+?\s*months?\s+(?:of\s+)?(?:professional\s+)?experience",
        re.IGNORECASE,
    ),
]


def _extract_experience_requirements(text: str) -> tuple[float, Optional[float]]:
    """
    Extract min and max years of experience from JD text.
    Returns (min_years, max_years). max_years is None if not specified.
    """
    for pattern in EXPERIENCE_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            first = matches[0]
            if isinstance(first, tuple) and len(first) == 2:
                # Range pattern: "3-5 years" or "6-12 months"
                v1, v2 = float(first[0]), float(first[1])
                if "month" in pattern.pattern:
                    return round(v1 / 12.0, 2), round(v2 / 12.0, 2)
                return v1, v2
            elif isinstance(first, str):
                v = float(first)
                if "month" in pattern.pattern:
                    return round(v / 12.0, 2), None
                return v, None
    return 0.0, None


def _extract_skill_bullets(lines: list[str]) -> list[str]:
    """
    Extract skills from bullet-pointed or numbered lists.
    Returns cleaned list of skill strings.
    """
    skills = []
    for line in lines:
        line = line.strip()
        # Remove bullet characters
        line = re.sub(r"^[\•\-\*\·\>\◦\▪]\s*", "", line)
        # Remove numbering
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        if not line or len(line) < 2:
            continue
        # If line contains comma-separated skills, split them
        if "," in line and len(line) < 200:
            parts = [p.strip() for p in line.split(",")]
            skills.extend([p for p in parts if len(p) > 1])
        else:
            skills.append(line)
    return skills


def _split_jd_sections(text: str) -> dict[str, list[str]]:
    """
    Split JD text into: required_section, preferred_section, context_section.
    """
    lines = text.splitlines()
    sections = {"required": [], "preferred": [], "context": []}
    current = "context"

    for line in lines:
        stripped = line.strip()
        if REQUIRED_SECTION_PATTERNS.search(stripped):
            current = "required"
        elif PREFERRED_SECTION_PATTERNS.search(stripped):
            current = "preferred"
        else:
            sections[current].append(stripped)

    return sections


def _extract_inline_skills(text: str) -> list[str]:
    """
    Fallback: extract skills from inline text using common JD phrasing.
    e.g., "experience with Python, SQL, and Spark"
    """
    skill_phrases = re.findall(
        r"(?:experience|proficiency|knowledge|familiarity|expertise|skills?)\s+"
        r"(?:in|with|using|of)?\s+([\w\s,\+\#\.\/]+?)(?:\.|\n|;|and\s+a|$)",
        text,
        re.IGNORECASE,
    )
    extracted = []
    for phrase in skill_phrases:
        parts = re.split(r"[,;]|\band\b", phrase)
        for part in parts:
            cleaned = part.strip().strip(".")
            if cleaned and len(cleaned) > 1 and len(cleaned) < 50:
                extracted.append(cleaned)
    return extracted


def parse_job_description(title: str, description_text: str) -> dict:
    """
    Main JD parsing function.

    Returns structured dict:
    {
        title, required_skills, preferred_skills,
        min_years_experience, max_years_experience,
        role_context, raw_text
    }
    """
    sections = _split_jd_sections(description_text)

    required_skills = _extract_skill_bullets(sections["required"])
    preferred_skills = _extract_skill_bullets(sections["preferred"])

    # Fallback: if section parsing yielded nothing, try inline extraction
    if not required_skills and not preferred_skills:
        inline = _extract_inline_skills(description_text)
        required_skills = inline

    min_years, max_years = _extract_experience_requirements(description_text)

    # Role context = full text summary for embedding-based matching
    role_context = " ".join(sections["context"]).strip()
    if not role_context:
        desc_str = str(description_text)
        # pyre-ignore[16]: Pyre fails to resolve str slice overload
        role_context = desc_str[0:500]  # first 500 chars as fallback

    logger.info(
        f"JD parsed | title='{title}' | required_skills={len(required_skills)} "
        f"| preferred={len(preferred_skills)} | min_yoe={min_years}"
    )

    return {
        "title": title,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "min_years_experience": min_years,
        "max_years_experience": max_years,
        "role_context": role_context,
        "raw_text": description_text,
    }
