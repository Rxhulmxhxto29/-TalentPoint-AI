"""
app/services/sample_loader.py — Automated sample data loading.

Populates the database with sample resumes if empty.
"""

import json
import logging
import sqlite3
from pathlib import Path

from app.services.resume_parser import parse_resume_file
from app.services.skill_extractor import get_skill_extractor
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

# Sample resume files in the project root
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"

def load_sample_data(db: sqlite3.Connection) -> None:
    """
    Check if the resumes table is empty.
    If yes, parse and index all files in data/samples/.
    """
    try:
        count = db.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
        if count > 0:
            logger.info(f"Database already has {count} resumes. Skipping sample loading.")
            return

        if not SAMPLES_DIR.exists():
            logger.warning(f"Samples directory {SAMPLES_DIR} not found.")
            return

        sample_files = list(SAMPLES_DIR.glob("*.txt"))
        if not sample_files:
            logger.info("No sample files found in data/samples/.")
            return

        logger.info(f"Found {len(sample_files)} samples. Starting automated indexing...")

        extractor = get_skill_extractor()
        embedding_svc = get_embedding_service()

        for file_path in sample_files:
            try:
                logger.info(f"Processing sample: {file_path.name}")
                
                # 1. Parse
                parsed = parse_resume_file(file_path)
                
                # 2. Normalize Skills
                raw_skills = parsed.get("skills", [])
                text_skills = extractor.extract_from_text(parsed.get("raw_text", ""))
                all_skills = list(set(extractor.extract_from_raw_list(raw_skills)) | set(text_skills))
                parsed["skills"] = sorted(all_skills)
                
                parsed_json = json.dumps(parsed)

                # 3. Save to DB
                cursor = db.execute(
                    """
                    INSERT INTO resumes (name, file_name, raw_text, parsed_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (parsed["name"], file_path.name, parsed["raw_text"], parsed_json),
                )
                resume_id = cursor.lastrowid
                db.commit()

                # 4. Index in FAISS
                embedding_svc.add_resume(resume_id, parsed["raw_text"])
                
                logger.info(f"Successfully indexed sample: {parsed['name']} (ID: {resume_id})")

            except Exception as e:
                logger.error(f"Failed to load sample {file_path.name}: {e}")
                db.rollback()

        logger.info("Automated sample indexing complete.")

    except Exception as e:
        logger.error(f"Error during sample data loading: {e}")
