"""
app/api/routers/jobs.py — Job description create, list, and detail endpoints.
"""

import json
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore

from app.api.dependencies import get_db  # type: ignore
from app.schemas.models import JobCreate  # type: ignore
from app.services.jd_parser import parse_job_description  # type: ignore
from app.services.skill_extractor import get_skill_extractor  # type: ignore
from config import DEFAULT_SCORING_WEIGHTS  # type: ignore

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Create a new job description.
    Parses required/preferred skills and experience requirements.
    """
    parsed = parse_job_description(payload.title, payload.description)

    # Normalize skills using extractor
    extractor = get_skill_extractor()
    parsed["required_skills"] = extractor.extract_from_raw_list(parsed["required_skills"])
    parsed["preferred_skills"] = extractor.extract_from_raw_list(parsed["preferred_skills"])

    # Also extract from full text (catch inline mentions)
    all_text_skills = extractor.extract_from_text(payload.description)
    # Add text-extracted skills that aren't already classified
    already_classified = set(
        s.lower() for s in parsed["required_skills"] + parsed["preferred_skills"]
    )
    extra = [s for s in all_text_skills if s.lower() not in already_classified]
    parsed["preferred_skills"] = sorted(set(parsed["preferred_skills"]) | set(extra))

    parsed_json = json.dumps(parsed)
    weights_json = json.dumps(DEFAULT_SCORING_WEIGHTS)

    cursor = db.execute(
        """
        INSERT INTO jobs (title, raw_text, parsed_json, weights_json, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (payload.title, payload.description, parsed_json, weights_json),
    )
    db.commit()
    job_id = cursor.lastrowid

    return {
        "message": "Job created successfully",
        "job_id": job_id,
        "title": payload.title,
        "required_skills": parsed["required_skills"],
        "preferred_skills": parsed["preferred_skills"],
        "min_years_experience": parsed["min_years_experience"],
    }


@router.get("/")
def list_jobs(db: sqlite3.Connection = Depends(get_db)):
    """List all job descriptions (summary view)."""
    rows = db.execute(
        "SELECT id, title, parsed_json, weights_json, created_at FROM jobs ORDER BY created_at DESC"
    ).fetchall()

    items = []
    for row in rows:
        parsed = json.loads(row["parsed_json"])
        items.append({
            "id": row["id"],
            "title": row["title"],
            "required_skill_count": len(parsed.get("required_skills", [])),
            "preferred_skill_count": len(parsed.get("preferred_skills", [])),
            "min_years_experience": parsed.get("min_years_experience", 0.0),
            "created_at": row["created_at"],
        })

    return {"jobs": items, "total": len(items)}


@router.get("/{job_id}")
def get_job(job_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Get full parsed job detail including current scoring weights."""
    row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "parsed": json.loads(row["parsed_json"]),
        "current_weights": json.loads(row["weights_json"]),
    }


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Delete a job description and its associated rankings."""
    row = db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    try:
        # 1. Delete feedback for all rankings of this job
        db.execute("DELETE FROM feedback WHERE ranking_id IN (SELECT id FROM rankings WHERE job_id = ?)", (job_id,))
        # 2. Delete other job-related logs
        db.execute("DELETE FROM bias_logs WHERE job_id = ?", (job_id,))
        db.execute("DELETE FROM weight_history WHERE job_id = ?", (job_id,))
        # 3. Delete the rankings themselves
        db.execute("DELETE FROM rankings WHERE job_id = ?", (job_id,))
        # 4. Finally delete the job
        db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        db.commit()
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(f"Delete job failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
