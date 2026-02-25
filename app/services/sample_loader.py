"""
app/services/sample_loader.py — Automated sample data loading.

Populates the database with sample resumes if empty.
"""

import json
import logging
import sqlite3
from pathlib import Path

from app.services.resume_parser import parse_resume_file  # type: ignore
from app.services.jd_parser import parse_job_description  # type: ignore
from app.services.skill_extractor import get_skill_extractor  # type: ignore
from app.services.embedding_service import get_embedding_service  # type: ignore
from app.services.ranking_service import rank_candidates  # type: ignore
from app.services.explainability_service import generate_explanations_for_ranking  # type: ignore

logger = logging.getLogger(__name__)

# Sample files in the project root
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"

def _load_resumes_for_ranking(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT id, name, parsed_json FROM resumes").fetchall() # type: ignore
    return [{"id": r["id"], "name": r["name"], "parsed": json.loads(r["parsed_json"])} for r in rows]

def _save_sample_rankings(db: sqlite3.Connection, job_id: int, ranked: list[dict]) -> None:
    db.execute("DELETE FROM rankings WHERE job_id = ?", (job_id,)) # type: ignore
    for candidate in ranked:
        db.execute( # type: ignore
            """
            INSERT INTO rankings
              (job_id, resume_id, rank, total_score, score_breakdown_json, 
               matched_skills_json, missing_skills_json, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                job_id, candidate["resume_id"], candidate["rank"], candidate["total_score"],
                json.dumps(candidate["score_breakdown"]), json.dumps(candidate.get("matched_skills", [])),
                json.dumps(candidate.get("missing_skills", [])), candidate.get("explanation", ""),
            ),
        )

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
                        cursor = db.execute(  # type: ignore
                            "INSERT INTO resumes (name, file_name, raw_text, parsed_json) VALUES (?, ?, ?, ?)",
                            (parsed["name"], file_path.name, parsed["raw_text"], parsed_json),
                        )
                        resume_id = cursor.lastrowid
                        embedding_svc.add_resume(resume_id, parsed["raw_text"])
                    except Exception as e:
                        logger.error(f"Failed to load resume sample {file_path.name}: {e}")
                db.commit()  # type: ignore

        # 2. Load Job Descriptions
        job_count = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]  # type: ignore
        last_job_id = None
        parsed_job_data = None
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
                        
                        cursor = db.execute(  # type: ignore
                            """
                            INSERT INTO jobs (title, raw_text, parsed_json, weights_json)
                            VALUES (?, ?, ?, ?)
                            """,
                            (title, raw_text, json.dumps(parsed), json.dumps(weights)),
                        )
                        last_job_id = cursor.lastrowid
                        parsed_job_data = (parsed, weights)
                    except Exception as e:
                        logger.error(f"Failed to load job sample {file_path.name}: {e}")
                db.commit()  # type: ignore

        # 3. Trigger Initial Ranking (if we have a job and resumes)
        if last_job_id and parsed_job_data:
            logger.info(f"Triggering automated ranking for Job ID: {last_job_id}")
            try:
                parsed_job, weights = parsed_job_data
                resumes = _load_resumes_for_ranking(db)
                if resumes:
                    ranked = rank_candidates(
                        parsed_resumes=resumes,
                        parsed_job=parsed_job,
                        weights=weights,
                        embedding_service=get_embedding_service()
                    )
                    ranked = generate_explanations_for_ranking(
                        ranked, min_required_yoe=parsed_job.get("min_years_experience", 0.0)
                    )
                    _save_sample_rankings(db, last_job_id, ranked)
                    db.commit()  # type: ignore
            except Exception as e:
                logger.error(f"Failed initial automated ranking: {e}")

    except Exception as e:
        logger.error(f"Error during sample data loading: {e}")
