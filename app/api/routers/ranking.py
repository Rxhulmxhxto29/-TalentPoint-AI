"""
app/api/routers/ranking.py — Candidate ranking endpoints.

POST /rank/{job_id}       → Run multi-factor ranking of all resumes vs this job
GET  /rank/{job_id}/results → Fetch the most recent saved rankings for a job
"""

import json
import sqlite3
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore

from app.api.dependencies import get_db  # type: ignore
from app.services.ranking_service import rank_candidates  # type: ignore
from app.services.explainability_service import generate_explanations_for_ranking  # type: ignore
from app.services.embedding_service import get_embedding_service  # type: ignore

router = APIRouter()


def _load_all_resumes(db: sqlite3.Connection) -> list[dict]:
    """Fetch all resumes from DB in the format expected by rank_candidates."""
    rows = db.execute(
        "SELECT id, name, parsed_json FROM resumes ORDER BY id"
    ).fetchall()

    resumes = []
    for row in rows:
        parsed = json.loads(row["parsed_json"])
        resumes.append({"id": row["id"], "name": row["name"], "parsed": parsed})
    return resumes


def _save_rankings(
    db: sqlite3.Connection,
    job_id: int,
    ranked: list[dict],
) -> None:
    """Persist ranking results to the rankings table."""
    # Clear previous rankings for this job
    db.execute("DELETE FROM rankings WHERE job_id = ?", (job_id,))

    for candidate in ranked:
        db.execute(
            """
            INSERT INTO rankings
              (job_id, resume_id, rank, total_score,
               score_breakdown_json, matched_skills_json,
               missing_skills_json, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                candidate["resume_id"],
                candidate["rank"],
                candidate["total_score"],
                json.dumps(candidate["score_breakdown"]),
                json.dumps(candidate.get("matched_skills", [])),
                json.dumps(candidate.get("missing_skills", [])),
                candidate.get("explanation", ""),
                datetime.utcnow().isoformat(),
            ),
        )
    db.commit()


@router.post("/{job_id}", status_code=status.HTTP_200_OK)
def run_ranking(job_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Rank all resumes against the specified job.

    Returns ranked list with per-candidate scores and explanations.
    Overwrites any previous ranking for this job.
    """
    # Fetch job
    job_row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job_row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    parsed_job = json.loads(job_row["parsed_json"])
    parsed_job["raw_text"] = job_row["raw_text"]
    weights = json.loads(job_row["weights_json"])

    # Fetch all resumes
    resumes = _load_all_resumes(db)
    if not resumes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No resumes in the system. Upload at least one resume before ranking.",
        )

    # Run ranking pipeline
    embedding_svc = get_embedding_service()
    ranked = rank_candidates(
        parsed_resumes=resumes,
        parsed_job=parsed_job,
        weights=weights,
        embedding_service=embedding_svc,
    )

    # Generate explanations
    ranked = generate_explanations_for_ranking(
        ranked,
        min_required_yoe=parsed_job.get("min_years_experience", 0.0),
    )

    # Persist
    _save_rankings(db, job_id, ranked)

    return {
        "job_id": job_id,
        "job_title": job_row["title"],
        "candidate_count": len(ranked),
        "weights_used": weights,
        "ranked_candidates": ranked,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/{job_id}/results")
def get_ranking_results(job_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Fetch the most recent saved ranking for a job (without re-running)."""
    job_row = db.execute("SELECT id, title, weights_json FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job_row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    ranking_rows = db.execute(
        """
        SELECT r.*, res.name as candidate_name
        FROM rankings r
        JOIN resumes res ON res.id = r.resume_id
        WHERE r.job_id = ?
        ORDER BY r.rank ASC
        """,
        (job_id,),
    ).fetchall()

    if not ranking_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No rankings found for job {job_id}. Run POST /rank/{job_id} first.",
        )

    candidates = []
    for row in ranking_rows:
        candidates.append({
            "ranking_id": row["id"],
            "rank": row["rank"],
            "resume_id": row["resume_id"],
            "candidate_name": row["candidate_name"],
            "total_score": row["total_score"],
            "score_breakdown": json.loads(row["score_breakdown_json"]),
            "matched_skills": json.loads(row["matched_skills_json"]),
            "missing_skills": json.loads(row["missing_skills_json"]),
            "explanation": row["explanation"],
            "created_at": row["created_at"],
        })

    return {
        "job_id": job_id,
        "job_title": job_row["title"],
        "weights_used": json.loads(job_row["weights_json"]),
        "candidate_count": len(candidates),
        "ranked_candidates": candidates,
    }


@router.get("/{job_id}/report.pdf")
def download_ranking_report(job_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Generate and stream a professional PDF ranking report for the given job."""
    import io
    from fastapi.responses import StreamingResponse  # type: ignore
    from app.services.report_service import report_service  # type: ignore

    job_row = db.execute("SELECT id, title, weights_json FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job_row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    ranking_rows = db.execute(
        """
        SELECT r.*, res.name as candidate_name
        FROM rankings r
        JOIN resumes res ON res.id = r.resume_id
        WHERE r.job_id = ?
        ORDER BY r.rank ASC
        """,
        (job_id,),
    ).fetchall()

    if not ranking_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No rankings for job {job_id}. Run ranking first.",
        )

    candidates = []
    for row in ranking_rows:
        candidates.append({
            "rank": row["rank"],
            "resume_id": row["resume_id"],
            "candidate_name": row["candidate_name"],
            "total_score": row["total_score"],
            "score_breakdown": json.loads(row["score_breakdown_json"]),
            "matched_skills": json.loads(row["matched_skills_json"]),
            "missing_skills": json.loads(row["missing_skills_json"]),
            "explanation": row["explanation"],
        })

    weights = json.loads(job_row["weights_json"])
    pdf_bytes = report_service.generate_ranking_report(job_row["title"], candidates, weights)
    safe_title = job_row["title"].replace(" ", "_").lower()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ranking_{safe_title}.pdf"},
    )
