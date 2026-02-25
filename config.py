"""
config.py — Central configuration for the AI Resume Screening System.

All tunable parameters, paths, and model identifiers live here.
Services import from this module — no hardcoded values in business logic.
"""

import os
from pathlib import Path

# ==============================================================================
# Base Paths
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_RESUMES_DIR = DATA_DIR / "sample" / "resumes"
SAMPLE_JOBS_DIR = DATA_DIR / "sample" / "jobs"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
PROCESSED_DIR = DATA_DIR / "processed"

# ==============================================================================
# Database
# ==============================================================================

DATABASE_PATH = BASE_DIR / "data" / "resume_screening.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# ==============================================================================
# ML Model Configuration
# ==============================================================================

# Sentence-BERT model — downloads ~80MB on first use (free, local)
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # MiniLM output dimension

# spaCy model — install via: python -m spacy download en_core_web_sm
SPACY_MODEL_NAME = "en_core_web_sm"

# FAISS index file
FAISS_INDEX_PATH = EMBEDDINGS_DIR / "resume_index.faiss"
FAISS_ID_MAP_PATH = EMBEDDINGS_DIR / "resume_id_map.pkl"

# ==============================================================================
# Scoring Weights (Multi-Factor Ranking)
# These are the DEFAULT weights. They are adjusted by the feedback service
# and stored in the database. The values here serve as initialization defaults.
# ==============================================================================

DEFAULT_SCORING_WEIGHTS = {
    "skill_match": 0.40,        # Jaccard + embedding similarity on skills
    "experience_alignment": 0.30,  # YoE match against job requirement
    "role_relevance": 0.30,     # Full-doc cosine similarity (resume vs JD)
}

# ==============================================================================
# Feedback Learning Configuration
# ==============================================================================

FEEDBACK_THRESHOLD = 5          # Trigger weight recalibration after N feedback entries
WEIGHT_LEARNING_RATE = 0.05     # Step size for EMA weight adjustment
MIN_WEIGHT = 0.10               # No single factor can fall below this
MAX_WEIGHT = 0.70               # No single factor can exceed this

# ==============================================================================
# Skill Normalization — Canonical Skill Map
# Keys are variants; values are canonical forms.
# This is extended by embedding-based fuzzy matching at runtime.
# ==============================================================================

SKILL_NORMALIZATION_MAP = {
    # Machine Learning
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "computer vision": "Computer Vision",
    "cv": "Computer Vision",
    "reinforcement learning": "Reinforcement Learning",
    "rl": "Reinforcement Learning",

    # Python Ecosystem
    "python": "Python",
    "py": "Python",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "sklearn": "Scikit-Learn",
    "scikit-learn": "Scikit-Learn",
    "scikit learn": "Scikit-Learn",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "keras": "Keras",
    "matplotlib": "Matplotlib",
    "seaborn": "Seaborn",
    "plotly": "Plotly",
    "scipy": "SciPy",
    "huggingface": "Hugging Face",
    "transformers": "Hugging Face Transformers",

    # Data Engineering
    "sql": "SQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "spark": "Apache Spark",
    "pyspark": "PySpark",
    "airflow": "Apache Airflow",
    "kafka": "Apache Kafka",
    "hadoop": "Hadoop",
    "hive": "Hive",
    "dbt": "dbt",

    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ci/cd": "CI/CD",
    "github actions": "GitHub Actions",

    # Web & API
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "rest api": "REST API",
    "restful": "REST API",
    "graphql": "GraphQL",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "react": "React",
    "reactjs": "React",
    "node.js": "Node.js",
    "nodejs": "Node.js",

    # MLOps
    "mlflow": "MLflow",
    "mlops": "MLOps",
    "model monitoring": "Model Monitoring",
    "feature engineering": "Feature Engineering",
    "a/b testing": "A/B Testing",

    # Project Management & Strategy
    "pmp": "Project Management",
    "project management": "Project Management",
    "program management": "Program Management",
    "agile": "Agile",
    "scrum": "Scrum",
    "kanban": "Kanban",
    "six sigma": "Six Sigma",
    "lean": "Lean",
    "stakeholder management": "Stakeholder Management",
    "stakeholder": "Stakeholder Management",
    "stakeholders": "Stakeholder Management",
    "risk assessment": "Risk Management",
    "risk management": "Risk Management",
    "risks": "Risk Management",
    "strategic planning": "Strategic Planning",
    "business strategy": "Strategic Planning",
    "resource allocation": "Resource Planning",
    "budgeting": "Budget Management",
    "cost control": "Budget Management",
    "vendor management": "Vendor Management",
    "change management": "Change Management",

    # Operations & HR
    "operations management": "Operations Management",
    "supply chain": "Supply Chain",
    "logistics": "Logistics",
    "procurement": "Procurement",
    "talent acquisition": "Talent Acquisition",
    "recruitment": "Talent Acquisition",
    "onboarding": "Onboarding",
    "performance management": "Performance Management",
    "employee relations": "Employee Relations",
    "hris": "HRIS",
    "payroll": "Payroll",
    "succession planning": "Succession Planning",
    "organizational development": "Organizational Development",
    "kpi tracking": "KPI Tracking",
    "okr": "OKR",

    # Finance & Compliance
    "financial analysis": "Financial Analysis",
    "accounting": "Accounting",
    "audit": "Audit",
    "taxation": "Taxation",
    "forecasting": "Financial Forecasting",
    "compliance": "Compliance",
    "regulatory compliance": "Compliance",
    "aml": "Anti-Money Laundering",
    "kyc": "KYC",
    "legal research": "Legal Research",
    "contract negotiation": "Contract Negotiation",

    # General & Soft Skills
    "git": "Git",
    "linux": "Linux",
    "bash": "Bash",
    "shell scripting": "Bash",
    "jira": "Jira",
    "excel": "Excel",
    "tableau": "Tableau",
    "power bi": "Power BI",
    "communication": "Communication",
    "leadership": "Leadership",
    "problem solving": "Problem Solving",
    "negotiation": "Negotiation",
    "public speaking": "Public Speaking",
    "emotional intelligence": "Emotional Intelligence",
    "conflict resolution": "Conflict Resolution",
    "time management": "Time Management",
    "teamwork": "Teamwork",
}

# ==============================================================================
# API Configuration
# ==============================================================================

API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", 8000))
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# ==============================================================================
# Explainability Templates
# ==============================================================================

EXPLANATION_TEMPLATE = (
    "Ranked #{rank} with a total score of {total_score:.2f}. "
    "{strength_sentence}"
    "{weakness_sentence}"
    "Experience score: {experience_score:.2f}; Role relevance: {role_relevance_score:.2f}."
)
