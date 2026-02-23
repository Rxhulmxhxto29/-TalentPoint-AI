"""
app/database/init_db.py — SQLite schema initialization.

Creates all tables on startup if they don't exist.
Run directly or called from FastAPI lifespan.
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


CREATE_RESUMES_TABLE = """
CREATE TABLE IF NOT EXISTS resumes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    file_name   TEXT,
    raw_text    TEXT NOT NULL,
    parsed_json TEXT NOT NULL,       -- JSON: {skills, experience, education, summary}
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    raw_text        TEXT NOT NULL,
    parsed_json     TEXT NOT NULL,   -- JSON: {required_skills, preferred_skills, min_years_experience, context}
    weights_json    TEXT NOT NULL,   -- JSON: current scoring weights for this job
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_RANKINGS_TABLE = """
CREATE TABLE IF NOT EXISTS rankings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id              INTEGER NOT NULL REFERENCES jobs(id),
    resume_id           INTEGER NOT NULL REFERENCES resumes(id),
    rank                INTEGER NOT NULL,
    total_score         REAL NOT NULL,
    score_breakdown_json TEXT NOT NULL,  -- JSON: {skill_match, experience_alignment, role_relevance}
    matched_skills_json  TEXT NOT NULL,  -- JSON: list of matched skills
    missing_skills_json  TEXT NOT NULL,  -- JSON: list of missing required skills
    explanation         TEXT NOT NULL,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ranking_id      INTEGER NOT NULL REFERENCES rankings(id),
    job_id          INTEGER NOT NULL REFERENCES jobs(id),
    resume_id       INTEGER NOT NULL REFERENCES resumes(id),
    decision        TEXT NOT NULL CHECK(decision IN ('accept', 'reject')),
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_BIAS_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS bias_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL REFERENCES jobs(id),
    analysis_json   TEXT NOT NULL,   -- JSON: full bias report
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_WEIGHT_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS weight_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER REFERENCES jobs(id),  -- NULL = global default
    weights_json    TEXT NOT NULL,
    trigger         TEXT NOT NULL,               -- 'feedback' | 'manual' | 'init'
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

ALL_TABLES = [
    ("resumes", CREATE_RESUMES_TABLE),
    ("jobs", CREATE_JOBS_TABLE),
    ("rankings", CREATE_RANKINGS_TABLE),
    ("feedback", CREATE_FEEDBACK_TABLE),
    ("bias_logs", CREATE_BIAS_LOGS_TABLE),
    ("weight_history", CREATE_WEIGHT_HISTORY_TABLE),
]


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Return a SQLite connection with foreign key enforcement enabled."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row          # dict-like row access
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # better concurrent read performance
    return conn


def initialize_database(db_path: Path) -> None:
    """
    Create all tables if they do not already exist.
    Safe to call on every startup — idempotent.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    try:
        with conn:
            for table_name, ddl in ALL_TABLES:
                conn.execute(ddl)
                logger.debug(f"Table ensured: {table_name}")
        logger.info(f"Database initialized at: {db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from config import DATABASE_PATH  # type: ignore
    logging.basicConfig(level=logging.INFO)
    initialize_database(DATABASE_PATH)
    print(f"Database ready: {DATABASE_PATH}")
