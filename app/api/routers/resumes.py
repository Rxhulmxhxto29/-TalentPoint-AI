"""
app/api/routers/resumes.py — Resume upload, parsing, and management endpoints.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status  # type: ignore
from fastapi.responses import StreamingResponse  # type: ignore

from app.api.dependencies import get_db  # type: ignore
from app.services.resume_parser import parse_resume_file, parse_resume_text  # type: ignore
from app.services.skill_extractor import get_skill_extractor  # type: ignore
from app.services.embedding_service import get_embedding_service  # type: ignore
from app.services.report_service import report_service  # type: ignore

router = APIRouter()


def _row_to_list_item(row: sqlite3.Row) -> dict:
    parsed = json.loads(row["parsed_json"])
    return {
        "id": row["id"],
        "name": row["name"],
        "file_name": row["file_name"],
        "total_years_experience": parsed.get("total_years_experience", 0.0),
        "skill_count": len(parsed.get("skills", [])),
        "created_at": row["created_at"],
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db),
):
    """
    Upload a resume file (PDF, DOCX, or TXT).
    Parses, normalizes skills, indexes embedding, stores in DB.
    """
    allowed_types = {
        "application/pdf", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    suffix_map = {
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
    }

    content_type = file.content_type or ""
    # Fallback: infer from filename extension
    if content_type not in allowed_types and file.filename:
        ext = Path(file.filename).suffix.lower()
        content_type = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
        }.get(ext, content_type)

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: PDF, DOCX, TXT. Got: {content_type}",
        )

    suffix = suffix_map.get(content_type, ".txt")

    # Write to temp file for parser
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        parsed = parse_resume_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    # Normalize skills via extractor
    extractor = get_skill_extractor()
    raw_skills = parsed.get("skills", [])
    # Also scan full text for skills missed by section parser
    text_skills = extractor.extract_from_text(parsed.get("raw_text", ""))
    all_skills = list(set(extractor.extract_from_raw_list(raw_skills)) | set(text_skills))
    parsed["skills"] = sorted(all_skills)

    parsed_json = json.dumps(parsed)

    # Check for existing candidate with same name
    existing = db.execute(
        "SELECT id FROM resumes WHERE name = ?", (parsed["name"],)
    ).fetchone()

    if existing:
        resume_id = existing["id"]
        db.execute(
            """
            UPDATE resumes
            SET file_name = ?, raw_text = ?, parsed_json = ?, created_at = datetime('now')
            WHERE id = ?
            """,
            (file.filename, parsed["raw_text"], parsed_json, resume_id),
        )
        message = "Resume updated successfully"
    else:
        cursor = db.execute(
            """
            INSERT INTO resumes (name, file_name, raw_text, parsed_json, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (parsed["name"], file.filename, parsed["raw_text"], parsed_json),
        )
        resume_id = cursor.lastrowid
        message = "Resume uploaded and parsed successfully"

    db.commit()

    # Add to FAISS index
    try:
        embedding_svc = get_embedding_service()
        embedding_svc.add_resume(resume_id, parsed["raw_text"])
    except Exception as e:
        # Non-fatal — resume stored, ranking will still work
        import logging
        logging.getLogger(__name__).warning(f"FAISS indexing failed for resume {resume_id}: {e}")

    return {
        "message": message,
        "resume_id": resume_id,
        "candidate_name": parsed["name"],
        "skills_extracted": len(parsed["skills"]),
        "total_years_experience": parsed["total_years_experience"],
    }


@router.post("/upload-text", status_code=status.HTTP_201_CREATED)
async def upload_resume_text(
    name: str = Form(...),
    raw_text: str = Form(...),
    db: sqlite3.Connection = Depends(get_db),
):
    """Upload a resume as raw text (for demo/testing without file upload)."""
    parsed = parse_resume_text(raw_text, filename=name)
    extractor = get_skill_extractor()
    text_skills = extractor.extract_from_text(raw_text)
    section_skills = extractor.extract_from_raw_list(parsed.get("skills", []))
    parsed["skills"] = sorted(set(section_skills) | set(text_skills))
    parsed["name"] = name  # override with provided name

    parsed_json = json.dumps(parsed)

    # Check for existing candidate with same name
    existing = db.execute(
        "SELECT id FROM resumes WHERE name = ?", (name,)
    ).fetchone()

    if existing:
        resume_id = existing["id"]
        db.execute(
            """
            UPDATE resumes
            SET file_name = ?, raw_text = ?, parsed_json = ?, created_at = datetime('now')
            WHERE id = ?
            """,
            (f"{name}.txt", raw_text, parsed_json, resume_id),
        )
        message = "Resume text updated successfully"
    else:
        cursor = db.execute(
            """
            INSERT INTO resumes (name, file_name, raw_text, parsed_json, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (name, f"{name}.txt", raw_text, parsed_json),
        )
        resume_id = cursor.lastrowid
        message = "Resume text uploaded successfully"

    db.commit()

    try:
        embedding_svc = get_embedding_service()
        embedding_svc.add_resume(resume_id, raw_text)
    except Exception:
        pass

    return {
        "message": message,
        "resume_id": resume_id,
        "candidate_name": name,
        "skills_extracted": len(parsed["skills"]),
        "total_years_experience": parsed["total_years_experience"],
    }


@router.get("/")
def list_resumes(db: sqlite3.Connection = Depends(get_db)):
    """List all resumes (summary view)."""
    rows = db.execute(
        "SELECT id, name, file_name, parsed_json, created_at FROM resumes ORDER BY created_at DESC"
    ).fetchall()
    return {"resumes": [_row_to_list_item(r) for r in rows], "total": len(rows)}


@router.get("/{resume_id}/pdf")
def download_resume_pdf(resume_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Generate and download a PDF version of the resume."""
    import io
    row = db.execute("SELECT name, raw_text FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")
    pdf_bytes = report_service.generate_resume_pdf(row["name"], row["raw_text"])
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=resume_{resume_id}.pdf"}
    )


@router.get("/{resume_id}")
def get_resume(resume_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Get full parsed resume detail."""
    row = db.execute(
        "SELECT * FROM resumes WHERE id = ?", (resume_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Resume {resume_id} not found")

    parsed = json.loads(row["parsed_json"])
    return {
        "id": row["id"],
        "name": row["name"],
        "file_name": row["file_name"],
        "raw_text": row["raw_text"],
        "created_at": row["created_at"],
        "parsed": parsed,
    }


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Delete a resume from DB and FAISS index."""
    row = db.execute("SELECT id FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Resume {resume_id} not found")

    db.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
    db.commit()

    try:
        get_embedding_service().remove_resume(resume_id)
    except Exception:
        pass
