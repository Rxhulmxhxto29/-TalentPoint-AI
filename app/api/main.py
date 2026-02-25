"""
app/api/main.py — FastAPI application entry point.

Startup sequence:
1. Initialize SQLite database (create tables if absent)
2. Load Sentence-BERT embedding model into memory
3. Load or create FAISS index from disk
4. Register all API routers

Run with:
    uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path when running from any directory
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

from config import DATABASE_PATH, API_HOST, API_PORT  # type: ignore
from app.database.init_db import initialize_database, get_connection  # type: ignore
from app.services.embedding_service import get_embedding_service  # type: ignore
from app.services.sample_loader import load_sample_data  # type: ignore
from app.api.routers import resumes, jobs, ranking, feedback, bias  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ==============================================================================
# Lifespan — Startup / Shutdown
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    All startup logic runs before yield; shutdown logic after yield.
    """
    # --- STARTUP ---
    logger.info("=== AI Resume Screening System — Startup ===")

    # 1. Database
    logger.info("Initializing database...")
    initialize_database(DATABASE_PATH)

    # 2. Embedding model (loads ~80MB MiniLM model on first call)
    logger.info("Loading Sentence-BERT embedding model (may take 10-30s first time)...")
    embedding_svc = get_embedding_service()
    embedding_svc.load_model()
    embedding_svc.load_or_create_index()
    logger.info("Embedding model and FAISS index ready.")

    # 3. Sample Data (automated indexing if empty)
    logger.info("Checking for sample data...")
    conn = get_connection(DATABASE_PATH)
    try:
        load_sample_data(conn)
    finally:
        conn.close()

    logger.info(f"API ready at http://{API_HOST}:{API_PORT}")
    logger.info("=== Startup complete ===")

    yield  # App runs here

    # --- SHUTDOWN ---
    logger.info("Saving FAISS index to disk...")
    embedding_svc.save_index()
    logger.info("Shutdown complete.")


# ==============================================================================
# FastAPI App
# ==============================================================================

app = FastAPI(
    title="AI Resume Screening API",
    description=(
        "Explainable, bias-aware candidate ranking system. "
        "100% local — no paid APIs required."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow Streamlit UI to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for production flexibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# Routers
# ==============================================================================

app.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])
app.include_router(jobs.router,    prefix="/jobs",    tags=["Jobs"])
app.include_router(ranking.router, prefix="/rank",    tags=["Ranking"])
app.include_router(feedback.router,prefix="/feedback",tags=["Feedback"])
app.include_router(bias.router,    prefix="/bias",    tags=["Bias Analysis"])


# ==============================================================================
# Health Check
# ==============================================================================

@app.get("/health", tags=["System"])
def health_check():
    """Basic liveness check — returns 200 if API is running."""
    return {"status": "ok", "service": "AI Resume Screening API", "version": "1.0.0"}


@app.get("/", tags=["System"])
def root():
    return {
        "message": "AI Resume Screening API",
        "docs": "/docs",
        "health": "/health",
    }
