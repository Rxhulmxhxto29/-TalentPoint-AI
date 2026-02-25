"""
app/services/resume_parser.py — Resume ingestion and structured extraction.

Supports PDF (via PyMuPDF), DOCX (via python-docx), and plain text.
Outputs a structured dict matching ParsedResume schema.

Design: Parsing is rule-based + regex with spaCy NER assist.
No ML model dependency — keeps this service fast and testable.
"""

import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional heavy imports — guarded so unit tests can mock if not installed
# ---------------------------------------------------------------------------
try:
    # pyre-ignore[21]: Pyre fails to resolve optional dependency fitz
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed — PDF parsing unavailable")

try:
    # pyre-ignore[21]: Pyre fails to resolve optional dependency docx
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not installed — DOCX parsing unavailable")


# ---------------------------------------------------------------------------
# Section header patterns (case-insensitive)
# ---------------------------------------------------------------------------

SECTION_PATTERNS = {
    "skills": re.compile(
        r"^\s*(technical\s+)?skills?(\s+&\s+\w+)?:?\s*$", re.IGNORECASE
    ),
    "experience": re.compile(
        r"^\s*(work\s+|professional\s+)?experience:?\s*$", re.IGNORECASE
    ),
    "education": re.compile(
        r"^\s*education(al\s+background)?:?\s*$", re.IGNORECASE
    ),
    "summary": re.compile(
        r"^\s*(professional\s+)?(summary|profile|objective|about\s+me):?\s*$",
        re.IGNORECASE
    ),
}

# Patterns for extracting years of experience from text
YEARS_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?"
    r"(?:\s+(?:professional\s+)?(?:work\s+)?experience)?",
    re.IGNORECASE,
)

# New: Pattern for extracting months of experience
MONTHS_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\+?\s*(?:months?|mos?)(?:\s+of)?"
    r"(?:\s+(?:professional\s+)?(?:work\s+)?experience)?",
    re.IGNORECASE,
)

# Date range pattern for experience entries (e.g., "Jan 2020 – Mar 2023")
DATE_RANGE_PATTERN = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|"
    r"\d{4})"
    r"\s*[–—\-–to]+\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|"
    r"\d{4}|Present|Current|Now)",
    re.IGNORECASE,
)

# Name extraction heuristic: first non-empty line that looks like a name
NAME_PATTERN = re.compile(r"^[A-Z][a-zA-Z\-']+(?:\s+[A-Z][a-zA-Z\-']+){1,3}$")


def extract_text_from_pdf(file_path: Path) -> str:
    """Extract raw text from a PDF file using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) is not installed. Run: pip install PyMuPDF")
    text_blocks = []
    with fitz.open(str(file_path)) as doc:
        for page in doc:
            text_blocks.append(page.get_text("text"))
    return "\n".join(text_blocks)


def extract_text_from_docx(file_path: Path) -> str:
    """Extract raw text from a DOCX file using python-docx."""
    if not DOCX_AVAILABLE:
        raise RuntimeError("python-docx is not installed. Run: pip install python-docx")
    doc = DocxDocument(str(file_path))
    paragraphs = [para.text for para in doc.paragraphs]
    return "\n".join(paragraphs)


def extract_text_from_file(file_path: Path) -> str:
    """Dispatch text extraction based on file extension."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    elif suffix in (".txt", ".text", ""):
        return file_path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def _split_into_sections(lines: list[str]) -> dict[str, list[str]]:
    """
    Split resume lines into named sections based on header pattern matching.
    Returns a dict of {section_name: [lines]}.
    """
    sections: dict[str, list[str]] = {
        "header": [],
        "summary": [],
        "skills": [],
        "experience": [],
        "education": [],
        "other": [],
    }
    current_section = "header"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        matched_section = None
        for section_name, pattern in SECTION_PATTERNS.items():
            if pattern.match(stripped):
                matched_section = section_name
                break

        if matched_section:
            current_section = str(matched_section)
        else:
            # pyre-ignore[16]: Pyre fails to resolve dict access in this loop
            sections[current_section].append(stripped)

    return sections


def _extract_candidate_name(header_lines: list[str], filename: str) -> str:
    """
    Attempt to extract candidate name from header lines.
    Falls back to filename stem if no name-like pattern found.
    """
    header_list = list(header_lines)
    # pyre-ignore[16]: Pyre fails to resolve list slice overload
    for line in header_list[0:5]:  # name is almost always in top 5 lines
        line = line.strip()
        if NAME_PATTERN.match(line) and len(line.split()) >= 2:
            return line
    # Fallback: use filename without extension
    return Path(filename).stem.replace("_", " ").replace("-", " ").title()


def _compute_duration_years(start: str, end: str) -> float:
    """
    Approximate duration in years from date strings.
    Handles: 'YYYY', 'Mon YYYY', 'Present'/'Current'.
    """
    import datetime

    def parse_date(s: str) -> tuple[int, int]:
        # Try full month name
        match_full = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})", s, re.IGNORECASE)
        if match_full:
            months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
            month_idx = months.index(match_full.group(1).lower()[:3]) + 1
            return int(match_full.group(2)), month_idx
        
        # Try year only
        match_year = re.search(r"\d{4}", s)
        if match_year:
            return int(match_year.group()), 1
            
        return datetime.datetime.now().year, 1

    current = datetime.datetime.now()
    start_year, start_month = parse_date(start)
    
    if re.search(r"present|current|now", end, re.IGNORECASE):
        end_year, end_month = current.year, current.month
    else:
        end_year, end_month = parse_date(end)

    total_months = (end_year - start_year) * 12 + (end_month - start_month)
    return max(0.0, float(round(total_months / 12.0, 2)))  # type: ignore


def _parse_experience_section(lines: list[str]) -> tuple[list[dict], float]:
    """
    Parse experience lines into structured entries.
    Returns: (experience_entries, total_years_experience)
    """
    entries = []
    total_years = 0.0
    current_entry: dict = {}
    description_buffer: list[str] = []

    def _flush_entry():
        nonlocal total_years
        if current_entry:
            current_entry["description"] = " ".join(description_buffer).strip()
            entries.append(dict(current_entry))
            total_years = total_years + current_entry.get("duration_years", 0.0)

    for line in lines:
        date_match = DATE_RANGE_PATTERN.search(line)
        if date_match:
            _flush_entry()
            current_entry = {}
            description_buffer = []
            duration = _compute_duration_years(
                date_match.group(1), date_match.group(2)
            )
            # The line before the date likely has the title/company
            line_str = str(line)
            # pyre-ignore[16]: Pyre fails to resolve str slice overload
            title_part = line_str[0:date_match.start()].strip().strip("–—|,")
            parts = re.split(r"\s*[|,@–—]\s*", title_part, maxsplit=1)
            current_entry = {
                "title": parts[0].strip() if parts else "",
                "company": parts[1].strip() if len(parts) > 1 else "",
                "date_range": f"{date_match.group(1)} – {date_match.group(2)}",
                "duration_years": duration,
            }
        else:
            description_buffer.append(line)

    _flush_entry()

    # If no date ranges found, try extracting total YoE from explicit statements
    if not entries:
        full_text = " ".join(lines)
        year_matches = YEARS_PATTERN.findall(full_text)
        month_matches = MONTHS_PATTERN.findall(full_text)
        
        yoe = 0.0
        if year_matches:
            yoe = max(float(y) for y in year_matches)
        
        if month_matches:
            # Add month-based experience (converted to fractional years) if year-based wasn't found or is smaller
            # This handles cases like "6 months experience" vs "0.5 years"
            mo_yoe = max(float(m) for m in month_matches) / 12.0
            total_years = max(yoe, float(round(mo_yoe, 2)))  # type: ignore
        else:
            total_years = yoe

    return entries, total_years


def _parse_education_section(lines: list[str]) -> list[dict[str, str]]:
    """Parse education lines into structured entries."""
    entries = []
    for line in lines:
        year_match = re.search(r"(19|20)\d{2}", line)
        year = year_match.group() if year_match else ""
        degree_keywords = [
            "bachelor", "master", "phd", "doctorate", "b.sc", "m.sc",
            "b.e", "m.e", "b.tech", "m.tech", "mba", "diploma", "certificate",
        ]
        degree = ""
        for kw in degree_keywords:
            if kw.lower() in line.lower():
                degree = line
                break
        if degree or year:
            entries.append({"degree": degree or line, "institution": "", "year": year})
    return entries


def parse_resume_text(raw_text: str, filename: str = "resume") -> dict:
    """
    Main parsing function — accepts raw text, returns structured dict.
    This is the core contract: text → {name, skills, experience, education, summary}.
    """
    lines = raw_text.splitlines()
    sections = _split_into_sections(lines)

    name = _extract_candidate_name(sections["header"], filename)

    experience_entries, total_years = _parse_experience_section(
        sections["experience"]
    )

    # If YoE still 0, scan full text for explicit statement
    if total_years == 0.0:
        year_matches = YEARS_PATTERN.findall(raw_text)
        if year_matches:
            total_years = max(float(y) for y in year_matches)

    education = _parse_education_section(sections["education"])
    summary = " ".join(sections["summary"])

    # Skills are raw lines — skill_extractor service normalizes them
    raw_skills = []
    for line in sections["skills"]:
        # Handle bullet-separated and comma-separated skill lists
        line = re.sub(r"^[\•\-\*\·]\s*", "", line)  # strip bullet chars
        parts = re.split(r"[,;|]", line)
        raw_skills.extend([p.strip() for p in parts if p.strip()])

    return {
        "name": name,
        "skills": raw_skills,  # will be normalized by skill_extractor
        "experience_entries": experience_entries,
        "total_years_experience": float(int(float(total_years) * 10) / 10.0),
        "education": education,
        "summary": summary,
        "raw_text": raw_text,
    }


def parse_resume_file(file_path: Path) -> dict:
    """
    End-to-end pipeline: file → extracted text → structured dict.
    Called by the API router on upload.
    """
    logger.info(f"Parsing resume: {file_path.name}")
    raw_text = extract_text_from_file(file_path)
    return parse_resume_text(raw_text, filename=file_path.name)
