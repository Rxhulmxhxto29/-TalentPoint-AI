"""
app/services/sample_loader.py — Automated sample data loading.

Populates the database with sample resumes if empty.
"""

import json
import logging
import sqlite3
from pathlib import Path

from app.services.resume_parser import parse_resume_file
from app.services.jd_parser import parse_job_description
from app.services.skill_extractor import get_skill_extractor
from app.services.embedding_service import get_embedding_service
from app.services.ranking_service import ranking_service

logger = logging.getLogger(__name__)

# Sample files in the project root
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"

def load_sample_data(db: sqlite3.Connection) -> None:
    """
    Check if the resumes and jobs tables are empty.
    If yes, parse and index samples from data/samples/.
    """
    try:
        # 1. Load Resumes
        resume_count = db.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
        if resume_count == 0:
            sample_resumes = list(SAMPLES_DIR.glob("resume_*.txt"))
            if sample_resumes:
                logger.info(f"Indexing {len(sample_resumes)} sample resumes...")
                extractor = get_skill_extractor()
                embedding_svc = get_embedding_service()

                for file_path in sample_resumes:
                    try:
                        parsed = parse_resume_file(file_path)
                        raw_skills = parsed.get("skills", [])
                        text_skills = extractor.extract_from_text(parsed.get("raw_text", ""))
                        all_skills = list(set(extractor.extract_from_raw_list(raw_skills)) | set(text_skills))
                        parsed["skills"] = sorted(all_skills)
                        
                        parsed_json = json.dumps(parsed)
                        cursor = db.execute(
                            "INSERT INTO resumes (name, file_name, raw_text, parsed_json) VALUES (?, ?, ?, ?)",
                            (parsed["name"], file_path.name, parsed["raw_text"], parsed_json),
                        )
                        resume_id = cursor.lastrowid
                        embedding_svc.add_resume(resume_id, parsed["raw_text"])
                    except Exception as e:
                        logger.error(f"Failed to load resume sample {file_path.name}: {e}")
                db.commit()

        # 2. Load Job Descriptions
        job_count = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        last_job_id = None
        if job_count == 0:
            sample_jobs = list(SAMPLES_DIR.glob("job_*.txt"))
            if sample_jobs:
                logger.info(f"Indexing {len(sample_jobs)} sample jobs...")
                for file_path in sample_jobs:
                    try:
                        raw_text = file_path.read_text(encoding="utf-8")
                        title = raw_text.splitlines()[0] if raw_text else "Untitled Role"
                        parsed = parse_job_description(title, raw_text)
                        
                        # Default weights
                        weights = {"skill_match": 0.4, "experience_alignment": 0.3, "role_relevance": 0.3}
                        
                        cursor = db.execute(
                            """
                            INSERT INTO jobs (title, raw_text, parsed_json, weights_json)
                            VALUES (?, ?, ?, ?)
                            """,
                            (title, raw_text, json.dumps(parsed), json.dumps(weights)),
                        )
                        last_job_id = cursor.lastrowid
                    except Exception as e:
                        logger.error(f"Failed to load job sample {file_path.name}: {e}")
                db.commit()

        # 3. Trigger Initial Ranking (if we have a job and resumes)
        if last_job_id:
            logger.info(f"Triggering automated ranking for Job ID: {last_job_id}")
            try:
                ranking_service.rank_resumes(last_job_id, db)
                db.commit()
            except Exception as e:
                logger.error(f"Failed initial automated ranking: {e}")

    except Exception as e:
        logger.error(f"Error during sample data loading: {e}")
