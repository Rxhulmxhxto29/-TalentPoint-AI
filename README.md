---
title: TalentPoint AI
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# TalentPoint AI — Smart Resume Ranking 🛡️📊

> **An enterprise-grade, explainable, and bias-aware Decision-Support System for modern recruitment.**
>
> 100% free and open-source · Fully Local NLP · No Cloud APIs · Mobile-Responsive UI

---

## The Vision

**TalentPoint AI** transforms the noisy process of manual resume screening into a precise, data-driven experience. Built for scale and fairness, it leverages deep semantic embeddings to understand candidate potential beyond simple keywords.

### 🌟 Key Enhancements
- **Mobile-First Experience**: High-density ranking tables that gracefully transform into elegant card-based views on smartphones.
- **Multi-Domain Intelligence**: Expanded support for Finance, Management, Operations, and HR domains.
- **Precision Experience Parsing**: High-precision "Month-to-Year" extraction ensures fair scoring for interns and fast-track talent.
- **Recruiter Feedback Loop**: A production-ready learning loop that adapts scoring weights based on your hiring preferences.

---

## Architecture

```
                        ┌──────────────────────────────┐
                        │        Streamlit UI           │
                        │    (5-page enterprise app)    │
                        └──────────────┬───────────────┘
                                       │ HTTP (REST)
                        ┌──────────────▼───────────────┐
                        │        FastAPI Layer           │
                        │  /resumes /jobs /rank          │
                        │  /feedback /bias               │
                        └──────┬───────────┬────────────┘
                               │           │
              ┌────────────────▼──┐    ┌───▼──────────────────┐
              │    ML Services     │    │    SQLite Database     │
              │                    │    │                        │
              │ resume_parser      │    │ resumes               │
              │ jd_parser          │    │ jobs                  │
              │ skill_extractor    │    │ rankings              │
              │ embedding_service  │    │ feedback              │
              │ ranking_service    │    │ bias_logs             │
              │ explainability_svc │    │ weight_history        │
              │ bias_service       │    └────────────────────────┘
              │ feedback_service   │
              └────────┬───────────┘
                       │
              ┌────────▼───────────┐
              │  Local ML Models   │
              │ all-MiniLM-L6-v2  │  ← Sentence-BERT (~80MB, free)
              │ FAISS CPU index   │  ← Local vector search
              │ spaCy en_core_web │  ← NLP pipeline
              └────────────────────┘
```

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| API-first | FastAPI with typed Pydantic schemas at every boundary |
| ML as a service | Each model/algorithm is a stateless service class |
| Pipeline over monolith | Resume → Parse → Extract → Embed → Rank → Explain |
| Explainability-first | Every score has a human-readable breakdown |
| No vendor lock-in | Zero paid APIs, zero cloud dependencies |

---

## Project Structure

```
AIML Project/
├── config.py                    # Central config: paths, weights, skill map
├── requirements.txt
├── README.md
│
├── app/
│   ├── api/
│   │   ├── main.py              # FastAPI app, lifespan, CORS
│   │   ├── dependencies.py      # Shared DB dependency injection
│   │   └── routers/
│   │       ├── resumes.py       # Upload, list, delete resumes
│   │       ├── jobs.py          # Create, list, get jobs
│   │       ├── ranking.py       # Run and fetch rankings
│   │       ├── feedback.py      # Submit feedback, stats
│   │       └── bias.py          # Bias analysis report
│   │
│   ├── database/
│   │   └── init_db.py           # SQLite schema (6 tables)
│   │
│   ├── schemas/
│   │   └── models.py            # Pydantic v2 request/response models
│   │
│   └── services/                # Core ML logic — pure Python functions
│       ├── resume_parser.py     # PDF/DOCX/TXT → structured JSON
│       ├── jd_parser.py         # JD → required/preferred skills + YoE
│       ├── skill_extractor.py   # spaCy NLP + canonical normalization
│       ├── embedding_service.py # Sentence-BERT + FAISS index management
│       ├── ranking_service.py   # Multi-factor scorer + ranker
│       ├── explainability_service.py  # NL explanation generator
│       ├── bias_service.py      # Spearman-based bias signal detection
│       └── feedback_service.py  # EMA weight adaptation
│
├── ui/
│   └── app.py                   # Streamlit 5-page UI
│
├── data/
│   ├── sample/
│   │   ├── resumes/             # 5 varied sample resumes (.txt)
│   │   └── jobs/                # 3 sample job descriptions (.txt)
│   ├── embeddings/              # FAISS index + id map (auto-generated)
│   └── seed.py                  # Loads sample data via API
│
├── tests/
│   ├── conftest.py              # Shared fixtures + in-memory DB
│   ├── test_resume_parser.py
│   ├── test_skill_extractor.py
│   ├── test_ranking_service.py
│   ├── test_explainability_service.py
│   └── test_api_endpoints.py    # Integration tests with TestClient
│
└── experiments/                 # Isolated notebooks (not used in production)
    └── README.md
```

---

## Scoring Model

Candidates are ranked using three independent factors:

| Factor | Weight (default) | Method |
|--------|-----------------|--------|
| **Skill Match** | 40% | 60% Jaccard overlap + 40% embedding cosine similarity on skill sets |
| **Experience Alignment** | 30% | Normalized YoE vs. job requirement (asymmetric penalty) |
| **Role Relevance** | 30% | Full-document cosine similarity via Sentence-BERT |

**Total Score = 0.40 × skill + 0.30 × experience + 0.30 × relevance**

Weights are per-job and adapt over time via recruiter feedback (EMA).

### Experience Alignment Logic

```
if candidate_yoe < min_required:
    penalty = shortfall / min_required        # proportional
    score = max(0.0, 1.0 - penalty)

elif min_required ≤ candidate_yoe ≤ max_required:
    score = 1.0                               # perfect fit

else:  # over-qualified
    penalty = min(0.3, surplus × 0.04)       # mild, max 30%
    score = 1.0 - penalty
```

---

## Feedback Learning Loop

```
Recruiter accepts/rejects → Stored in feedback table
       ↓ (after every 5 decisions per job)
EMA signal = avg(accepted_factor_scores) - avg(rejected_factor_scores)
       ↓
new_weight = old_weight + learning_rate × signal
       ↓
Clamped to [0.10, 0.70], re-normalized to sum 1.0
       ↓
Saved to jobs.weights_json + logged to weight_history
```

No model retraining required. Fully auditable via `weight_history` table.

---

## Bias Analysis

Three signals are computed for each ranking:

| Signal | Method | Severity Trigger |
|--------|--------|-----------------|
| Experience Skew | Spearman rank correlation (YoE vs. total score) | > 0.45 |
| Keyword Overfit | Spearman rank correlation (skill_score vs. total) | > 0.50 |
| Factor Dominance | Weighted contribution per factor > 35% | Configurable |

Every bias report includes a mandatory ethical disclaimer.

---

## Setup & Running

### 1. Install Dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

> **Note:** `sentence-transformers` will download `all-MiniLM-L6-v2` (~80MB) on first run.

### 2. Start the API

```bash
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

API docs available at: http://127.0.0.1:8000/docs

### 3. Load Sample Data

```bash
python data/seed.py
```

### 4. Start the UI

```bash
streamlit run ui/app.py
```

Open: http://localhost:8501

---

## Running Tests

```bash
pytest tests/ -v
```

Tests use in-memory SQLite and mock the embedding model — no real model download needed for tests.

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| API | FastAPI | Modern, typed, async-capable |
| UI | Streamlit | Rapid internal tooling |
| NLP | spaCy en_core_web_sm | Lightweight, production-ready |
| Embeddings | Sentence-BERT `all-MiniLM-L6-v2` | Best free local semantic model |
| Vector Search | FAISS CPU | Free, local, no infrastructure |
| ML | scikit-learn | Stable, well-tested |
| Database | SQLite | Zero-config, fully portable |
| Doc Parsing | PyMuPDF + python-docx | Reliable PDF/DOCX extraction |

---

## Design Decisions & Trade-offs

### Why template-based explanations, not an LLM?
LLMs introduce non-determinism — same inputs can produce different outputs across runs. For a bias-aware, interview-defensible system, **deterministic explanations are critical**. Templates guarantee the same scores always produce the same explanation.

### Why EMA weight adaptation, not retraining?
Retraining requires significant labeled data (hundreds of feedback entries minimum), compute time, and validation engineering. EMA allows **continuous, stable improvement** from just 5 feedback entries per job, with no risk of catastrophic forgetting or model instability.

### Why FAISS CPU over a vector database?
Pinecone, Weaviate, and similar tools require paid plans or cloud accounts at scale. FAISS CPU provides **production-quality ANN search entirely locally** for corpora up to hundreds of thousands of resumes — more than sufficient for most HR environments.

### Why Jaccard + embedding blend for skill scoring?
Pure Jaccard penalizes candidates who describe the same skill differently ("ML" vs "Machine Learning"). Pure embedding similarity is too permissive — it may match unrelated domains with similar phrasing. The **60% Jaccard / 40% embedding blend** balances precision and recall.

---

## Limitations

- **Resume parsing accuracy:** Section detection is regex-based. Unusual resume formats (tables, columns, graphics) may not parse correctly. PDF files with scanned images (no text layer) are not supported.
- **Skill coverage:** The canonical skill map covers ~80 common skills. Highly domain-specific or emerging skills will fall through to title-case normalization rather than canonical mapping.
- **Bias detection:** Bias signals are correlational, not causal. A high experience-skew score may reflect a legitimate job requirement, not an unfair bias.
- **Feedback quality:** EMA learning assumes recruiter decisions are consistent. High noise in feedback will degrade weight accuracy.
- **Scale:** SQLite and FAISS CPU are sufficient for up to ~50K resumes. Beyond that, migrate to PostgreSQL + FAISS with IVF indexing.

---

## Future Improvements

- [ ] PDF OCR support (Tesseract) for scanned resumes
- [ ] Structured skill taxonomy using ESCO/O*NET ontology
- [ ] Vector database migration (Chroma for free local use)
- [ ] A/B testing framework for comparing scoring weight configurations
- [ ] Batch resume upload with progress tracking
- [ ] REST API authentication (JWT)
- [ ] Diversity metric tracking across candidate pool demographics
- [ ] Export ranking results to CSV/PDF
- [ ] Multi-language resume support

---

## Evaluation Metrics

This system is evaluated on:

| Metric | Description |
|--------|-------------|
| **Precision@K** | Of top-K ranked candidates, how many are accepted by recruiter? |
| **Ranking Consistency** | Same inputs → same ranking (deterministic) |
| **Explainability Completeness** | All scored factors present in explanation? |
| **Bias Signal Coverage** | Are known bias patterns detected before recruiter sees ranking? |
| **Weight Convergence** | Do EMA-adjusted weights stabilize after N feedback cycles? |

---

## License

MIT License — free to use, modify, and distribute.
