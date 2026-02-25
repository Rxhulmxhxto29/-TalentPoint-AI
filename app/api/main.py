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
import asyncio
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
    Only lightweight DB init is synchronous — heavy work runs in background
    so the /health endpoint responds immediately and HF Spaces sees API as online.
    """
    # --- STARTUP ---
    logger.info("=== AI Resume Screening System — Startup ===")

    # 1. Database (fast — must complete before serving requests)
    logger.info("Initializing database...")
    initialize_database(DATABASE_PATH)
    logger.info("Database ready.")

    # 2. All heavy work in background so /health responds immediately
    async def _background_init():
        import asyncio as _asyncio
        await _asyncio.sleep(1)  # allow uvicorn to bind port first

        logger.info("Background: Loading Sentence-BERT model (may take 10-30s)...")
        try:
            embedding_svc = get_embedding_service()
            embedding_svc.load_model()
            embedding_svc.load_or_create_index()
            logger.info("Background: Embedding model and FAISS index ready.")
        except Exception as e:
            logger.error(f"Background: Embedding model load failed: {e}")

        logger.info("Background: Checking for sample data...")
        conn = get_connection(DATABASE_PATH)
        try:
            load_sample_data(conn)
            logger.info("Background: Sample data ready.")
        except Exception as e:
            logger.error(f"Background: Sample loading failed: {e}")
        finally:
            conn.close()

        logger.info("=== Background init complete ===")

    asyncio.create_task(_background_init())

    logger.info("API ready — heavy init running in background.")
    logger.info(f"Serving at http://{API_HOST}:{API_PORT}")

    yield  # App serves requests here

    # --- SHUTDOWN ---
    logger.info("Saving FAISS index to disk...")
    try:
        get_embedding_service().save_index()
    except Exception as e:
        logger.warning(f"FAISS save failed (non-fatal): {e}")
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
    """Liveness + readiness check. Reports whether AI model is loaded."""
    embedding_svc = get_embedding_service()
    model_ready = embedding_svc.is_ready
    return {
        "status": "ok",
        "service": "AI Resume Screening API",
        "version": "1.0.0",
        "model_ready": model_ready,
    }


@app.get("/", tags=["System"])
def root():
    return {
        "message": "AI Resume Screening API",
        "docs": "/docs",
        "health": "/health",
    }
