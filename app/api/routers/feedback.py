"""
app/api/routers/feedback.py — Recruiter feedback submission and statistics.
"""

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore

from app.api.dependencies import get_db  # type: ignore
from app.schemas.models import FeedbackCreate  # type: ignore
from app.services.feedback_service import (  # type: ignore
    store_feedback,
    get_feedback_stats,
    maybe_trigger_weight_adjustment,
)

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    db: sqlite3.Connection = Depends(get_db),
):
    """
    Submit recruiter accept/reject feedback for a ranked candidate.

    After every FEEDBACK_THRESHOLD submissions for a job, scoring weights
    are automatically adjusted via EMA learning.
    """
    # Validate ranking exists and fetch job_id + resume_id
    ranking_row = db.execute(
        "SELECT id, job_id, resume_id FROM rankings WHERE id = ?",
        (payload.ranking_id,),
    ).fetchone()

    if not ranking_row:
        raise HTTPException(
            status_code=404,
            detail=f"Ranking entry {payload.ranking_id} not found. Run ranking first.",
        )

    job_id = ranking_row["job_id"]
    resume_id = ranking_row["resume_id"]

    # Store feedback
    feedback_id = store_feedback(
        conn=db,
        ranking_id=payload.ranking_id,
        job_id=job_id,
        resume_id=resume_id,
        decision=payload.decision,
        notes=payload.notes,
    )

    # Check if weight adjustment should be triggered
    new_weights = maybe_trigger_weight_adjustment(db, job_id)

    response = {
        "message": "Feedback recorded",
        "feedback_id": feedback_id,
        "job_id": job_id,
        "decision": payload.decision,
    }
    if new_weights:
        response["weight_adjustment_triggered"] = True
        response["new_weights"] = new_weights
    else:
        response["weight_adjustment_triggered"] = False

    return response


@router.get("/stats")
def feedback_statistics(db: sqlite3.Connection = Depends(get_db)):
    """Global feedback statistics across all jobs."""
    return get_feedback_stats(db)


@router.get("/job/{job_id}")
def feedback_for_job(job_id: int, db: sqlite3.Connection = Depends(get_db)):
    """List all feedback entries for a specific job."""
    rows = db.execute(
        """
        SELECT f.*, res.name as candidate_name
        FROM feedback f
        JOIN resumes res ON res.id = f.resume_id
        WHERE f.job_id = ?
        ORDER BY f.created_at DESC
        """,
        (job_id,),
    ).fetchall()

    return {
        "job_id": job_id,
        "feedback": [dict(row) for row in rows],
        "total": len(rows),
    }
