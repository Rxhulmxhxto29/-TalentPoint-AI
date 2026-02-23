"""
tests/conftest.py — Shared pytest fixtures for the resume screening system.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

import pytest  # type: ignore

# Ensure project root is on path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# In-memory test database
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db() -> Generator[sqlite3.Connection, None, None]:
    """Create an in-memory SQLite DB with the full schema for testing."""
    from app.database.init_db import ALL_TABLES  # type: ignore
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    for _, ddl in ALL_TABLES:
        conn.execute(ddl)
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Sample resume fixtures
# ---------------------------------------------------------------------------

SAMPLE_RESUME_TEXT_SENIOR = """
Priya Sharma
priya@email.com

SUMMARY
Senior ML Engineer with 7 years of experience.

SKILLS
Python, TensorFlow, PyTorch, scikit-learn, NLP, spaCy, Hugging Face Transformers, MLflow, Docker, Kubernetes, AWS, SQL, FastAPI

EXPERIENCE

Senior ML Engineer | TechCorp AI
Jan 2021 – Present
Led NLP team building production pipelines for 5M documents/day.

ML Engineer | Infosys AI Lab
Jul 2017 – Dec 2020
Built recommendation systems using collaborative filtering.

EDUCATION
M.Tech, CS | IIT Bombay | 2017
"""

SAMPLE_RESUME_TEXT_JUNIOR = """
Rahul Verma
rahul@gmail.com

OBJECTIVE
Junior data analyst with 1 year of experience.

SKILLS
Python, Pandas, SQL, Excel, Tableau, Matplotlib

EXPERIENCE

Junior Data Analyst | Analytics Co
Jun 2024 – Present
Built dashboards and SQL reports.

EDUCATION
B.Sc, Statistics | Mumbai University | 2023
"""

SAMPLE_JD_TEXT = """
Senior Machine Learning Engineer

Required Skills:
- Python
- Machine Learning
- NLP
- PyTorch or TensorFlow
- Docker
- SQL
- Git

Nice to Have:
- Kubernetes
- AWS
- FastAPI
- MLflow
- spaCy

Requirements:
Minimum 5 years of professional experience in ML engineering.
"""


@pytest.fixture
def parsed_senior_resume():
    from app.services.resume_parser import parse_resume_text  # type: ignore
    return parse_resume_text(SAMPLE_RESUME_TEXT_SENIOR, filename="priya_sharma.txt")


@pytest.fixture
def parsed_junior_resume():
    from app.services.resume_parser import parse_resume_text  # type: ignore
    return parse_resume_text(SAMPLE_RESUME_TEXT_JUNIOR, filename="rahul_verma.txt")


@pytest.fixture
def parsed_job():
    from app.services.jd_parser import parse_job_description  # type: ignore
    return parse_job_description("Senior ML Engineer", SAMPLE_JD_TEXT)


@pytest.fixture
def default_weights():
    return {"skill_match": 0.40, "experience_alignment": 0.30, "role_relevance": 0.30}


@pytest.fixture
def sample_ranked_candidates():
    """Pre-built ranked list for testing downstream services."""
    return [
        {
            "rank": 1,
            "resume_id": 1,
            "candidate_name": "Priya Sharma",
            "total_score": 0.82,
            "score_breakdown": {
                "skill_match": 0.85, "experience_alignment": 0.90,
                "role_relevance": 0.78, "total": 0.82,
            },
            "matched_skills": ["Python", "NLP", "PyTorch", "Docker"],
            "missing_skills": [],
            "candidate_years_experience": 7.0,
            "explanation": "",
        },
        {
            "rank": 2,
            "resume_id": 2,
            "candidate_name": "Anika Patel",
            "total_score": 0.61,
            "score_breakdown": {
                "skill_match": 0.60, "experience_alignment": 0.70,
                "role_relevance": 0.55, "total": 0.61,
            },
            "matched_skills": ["Python", "Docker"],
            "missing_skills": ["NLP", "PyTorch"],
            "candidate_years_experience": 4.0,
            "explanation": "",
        },
        {
            "rank": 3,
            "resume_id": 3,
            "candidate_name": "Rahul Verma",
            "total_score": 0.33,
            "score_breakdown": {
                "skill_match": 0.25, "experience_alignment": 0.35,
                "role_relevance": 0.40, "total": 0.33,
            },
            "matched_skills": ["Python", "SQL"],
            "missing_skills": ["NLP", "PyTorch", "Docker", "MLflow"],
            "candidate_years_experience": 1.5,
            "explanation": "",
        },
    ]
