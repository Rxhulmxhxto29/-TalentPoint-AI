"""
app/services/embedding_service.py — Sentence-BERT embeddings and FAISS index management.

Uses all-MiniLM-L6-v2 (~80MB, free, local) for semantic similarity.
FAISS CPU index for efficient vector search across resume corpus.
"""

from __future__ import annotations

import pickle
import logging
import sys
from pathlib import Path
from typing import Any, Optional

# numpy — always required at runtime
import numpy as np  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency guards — allows module to be imported even when
# heavy packages are absent (unit tests, CI without GPU deps, etc.)
# ---------------------------------------------------------------------------
SENTENCE_TRANSFORMERS_AVAILABLE: bool = False
try:
    import sentence_transformers as _st_mod  # type: ignore[import-untyped]
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    _st_mod = None  # type: ignore[assignment]
    logger.error("sentence-transformers not installed! Run: pip install sentence-transformers")

FAISS_AVAILABLE: bool = False
try:
    import faiss as _faiss_mod  # type: ignore[import-untyped]
    FAISS_AVAILABLE = True
except ImportError:
    _faiss_mod = None  # type: ignore[assignment]
    logger.error("faiss-cpu not installed! Run: pip install faiss-cpu")


def _require_st() -> Any:
    """Return the SentenceTransformer class or raise."""
    if not SENTENCE_TRANSFORMERS_AVAILABLE or _st_mod is None:
        raise RuntimeError("sentence-transformers not installed")
    return getattr(_st_mod, "SentenceTransformer")


def _require_faiss() -> Any:
    """Return the faiss module or raise."""
    if not FAISS_AVAILABLE or _faiss_mod is None:
        raise RuntimeError("faiss-cpu not installed")
    return _faiss_mod


class EmbeddingService:
    """
    Central embedding and vector search service.

    Responsibilities:
    - Encode text → dense vectors via Sentence-BERT
    - Maintain FAISS index of all resume embeddings
    - Compute pairwise cosine similarity
    """

    def __init__(
        self,
        model_name: str,
        dimension: int,
        index_path: Path,
        id_map_path: Path,
    ) -> None:
        self.model_name  = model_name
        self.dimension   = dimension
        self.index_path  = index_path
        self.id_map_path = id_map_path

        self._model: Any       = None   # SentenceTransformer instance
        self._index: Any       = None   # faiss.Index instance
        self._id_map: list[int] = []    # position i → resume_id

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """Load Sentence-BERT model. Called once at startup."""
        ST: Any = _require_st()
        logger.info(f"Loading embedding model: {self.model_name}")
        self._model = ST(self.model_name)
        logger.info("Embedding model loaded successfully")

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Encode a list of texts into dense embedding vectors.
        Returns numpy array of shape (len(texts), dimension).
        """
        if self._model is None:
            raise RuntimeError("Embedding model not loaded. Call load_model() first.")
        if not texts:
            return np.array([]).reshape(0, self.dimension)

        result = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(result, dtype=np.float32)

    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Cosine similarity between two normalized vectors.
        L2-normalized embeddings → dot product == cosine similarity.
        """
        a = vec_a.reshape(1, -1) if vec_a.ndim == 1 else vec_a
        b = vec_b.reshape(1, -1) if vec_b.ndim == 1 else vec_b
        score = float(np.dot(a, b.T).squeeze())
        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # FAISS Index Management
    # ------------------------------------------------------------------

    def _make_index(self) -> Any:
        """Create a new FAISS flat inner-product index (exact search)."""
        fmod = _require_faiss()
        return fmod.IndexFlatIP(self.dimension)

    def load_or_create_index(self) -> None:
        """Load existing FAISS index from disk, or create a fresh empty index."""
        fmod = _require_faiss()
        if self.index_path.exists() and self.id_map_path.exists():
            logger.info(f"Loading FAISS index from: {self.index_path}")
            self._index = fmod.read_index(str(self.index_path))
            with open(self.id_map_path, "rb") as fh:
                self._id_map = pickle.load(fh)
            logger.info(f"FAISS index loaded: {self._index.ntotal} vectors, "
                        f"{len(self._id_map)} ids")
        else:
            logger.info("Creating new empty FAISS index")
            self._index = self._make_index()
            self._id_map = []

    def save_index(self) -> None:
        """Persist FAISS index and id map to disk."""
        if self._index is None:
            return
        fmod = _require_faiss()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        fmod.write_index(self._index, str(self.index_path))
        with open(self.id_map_path, "wb") as fh:
            pickle.dump(self._id_map, fh)
        logger.info(f"FAISS index saved: {self._index.ntotal} vectors")

    def add_resume(self, resume_id: int, text: str) -> np.ndarray:
        """
        Encode a resume text and add to FAISS index.
        Returns the embedding vector.
        """
        if self._index is None:
            self.load_or_create_index()

        embedding = self.encode([text])  # shape (1, dim)

        if resume_id in self._id_map:
            self._rebuild_index_without(resume_id)

        self._index.add(embedding)
        self._id_map.append(resume_id)
        self.save_index()
        logger.debug(f"Added resume_id={resume_id} to FAISS (total: {self._index.ntotal})")
        return embedding[0]

    def _rebuild_index_without(self, exclude_id: int) -> None:
        """Rebuild FAISS index excluding a specific resume_id."""
        if self._index is None or self._index.ntotal == 0:
            return

        n = int(self._index.ntotal)
        all_vecs = np.zeros((n, self.dimension), dtype=np.float32)
        for i in range(n):
            all_vecs[i] = self._index.reconstruct(i)

        new_vecs: list[np.ndarray] = []
        new_ids:  list[int]        = []
        for i, rid in enumerate(self._id_map):
            if rid != exclude_id:
                new_vecs.append(all_vecs[i])
                new_ids.append(rid)

        self._index   = self._make_index()
        self._id_map  = new_ids
        if new_vecs:
            self._index.add(np.array(new_vecs, dtype=np.float32))

    def remove_resume(self, resume_id: int) -> None:
        """Remove a resume from the FAISS index."""
        if resume_id not in self._id_map:
            return
        self._rebuild_index_without(resume_id)
        self.save_index()
        logger.info(f"Removed resume_id={resume_id} from FAISS index")

    def search_similar(self, query_text: str, k: int = 10) -> list[tuple[int, float]]:
        """
        Find the k most semantically similar resumes.
        Returns list of (resume_id, score) sorted by score descending.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        query_emb = self.encode([query_text])
        k_actual  = min(k, int(self._index.ntotal))
        # Cast index to Any to avoid "Unknown" call errors
        idx: Any = self._index
        scores, indices = idx.search(query_emb, k_actual)

        results: list[tuple[int, float]] = []
        # Cast scores/indices to Any to handle FAISS dynamic return types
        s_arr: Any = scores[0]
        i_arr: Any = indices[0]
        for score, pos in zip(s_arr, i_arr):
            if int(pos) < 0:
                continue
            results.append((self._id_map[int(pos)], float(max(0.0, score))))
        return results

    def get_resume_embedding(self, resume_text: str) -> np.ndarray:
        """Encode a single resume text."""
        return self.encode([resume_text])[0]

    def get_jd_embedding(self, jd_text: str) -> np.ndarray:
        """Encode a job description text."""
        return self.encode([jd_text])[0]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_embedding_service_instance: Optional["EmbeddingService"] = None


def get_embedding_service() -> "EmbeddingService":
    """
    Return the global EmbeddingService singleton.
    Creates it on first call; subsequent calls return the cached instance.
    """
    global _embedding_service_instance
    if _embedding_service_instance is not None:
        return _embedding_service_instance

    # Ensure project root is on path so `config` is importable from anywhere
    _root = str(Path(__file__).resolve().parents[2])
    if _root not in sys.path:
        sys.path.insert(0, _root)

    from config import (  # type: ignore
        EMBEDDING_MODEL_NAME,
        EMBEDDING_DIMENSION,
        FAISS_INDEX_PATH,
        FAISS_ID_MAP_PATH,
    )

    _embedding_service_instance = EmbeddingService(
        model_name=EMBEDDING_MODEL_NAME,
        dimension=EMBEDDING_DIMENSION,
        index_path=FAISS_INDEX_PATH,
        id_map_path=FAISS_ID_MAP_PATH,
    )
    return _embedding_service_instance
