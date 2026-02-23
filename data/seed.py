"""
data/seed.py — Load sample data into the system via the API.

Run AFTER starting the API:
    python data/seed.py

This populates the DB with 5 resumes and 3 job descriptions
for immediate demo-ready use.
"""

import sys
import time
from pathlib import Path

import requests  # type: ignore

API_BASE = "http://127.0.0.1:8000"
RESUMES_DIR = Path(__file__).parent / "sample" / "resumes"
JOBS_DIR    = Path(__file__).parent / "sample" / "jobs"

JOB_DEFINITIONS = [
    {
        "file": "senior_ml_engineer.txt",
        "title": "Senior ML Engineer",
    },
    {
        "file": "junior_data_analyst.txt",
        "title": "Junior Data Analyst",
    },
    {
        "file": "nlp_engineer.txt",
        "title": "NLP Engineer",
    },
]


def wait_for_api(max_retries: int = 10) -> bool:
    """Wait until the API is available."""
    for i in range(max_retries):
        try:
            r = requests.get(f"{API_BASE}/health", timeout=5)
            if r.status_code == 200:
                print(f"✅ API is ready at {API_BASE}")
                return True
        except requests.exceptions.ConnectionError:
            pass
        print(f"  Waiting for API... ({i+1}/{max_retries})")
        time.sleep(2)
    return False


def seed_resumes() -> int:
    """Upload all sample resume text files."""
    uploaded_ids = []
    for resume_path in sorted(RESUMES_DIR.glob("*.txt")):
        name = resume_path.stem.replace("_", " ").title()
        raw_text = resume_path.read_text(encoding="utf-8")

        resp = requests.post(
            f"{API_BASE}/resumes/upload-text",
            data={"name": name, "raw_text": raw_text},
            timeout=30,
        )
        if resp.status_code == 201:
            data = resp.json()
            print(
                f"  ✅ Resume: {data['candidate_name']} | "
                f"Skills: {data['skills_extracted']} | "
                f"YoE: {data['total_years_experience']}"
            )
            uploaded_ids.append(data.get("resume_id"))
        else:
            print(f"  ❌ Failed to upload {name}: {resp.text}")
    return len(uploaded_ids)


def seed_jobs() -> int:
    """Create all sample job descriptions."""
    created_jobs = []
    for job_def in JOB_DEFINITIONS:
        job_path = JOBS_DIR / job_def["file"]
        if not job_path.exists():
            print(f"  ⚠️  Job file not found: {job_path}")
            continue

        description = job_path.read_text(encoding="utf-8")
        resp = requests.post(
            f"{API_BASE}/jobs/",
            json={"title": job_def["title"], "description": description},
            timeout=30,
        )
        if resp.status_code == 201:
            data = resp.json()
            print(
                f"  ✅ Job: {data['title']} (ID: {data['job_id']}) | "
                f"Required skills: {len(data.get('required_skills', []))}"
            )
            created_jobs.append(data.get("job_id"))
        else:
            print(f"  ❌ Failed to create job '{job_def['title']}': {resp.text}")
    return len(created_jobs)


def main():
    print("\n=== AI Resume Screening — Data Seeder ===\n")

    if not wait_for_api():
        print("\n❌ API is not available. Start it with:")
        print("   uvicorn app.api.main:app --reload\n")
        sys.exit(1)

    print("\n📄 Seeding resumes...")
    n_resumes = seed_resumes()

    print("\n🏢 Seeding job descriptions...")
    n_jobs = seed_jobs()

    print(f"\n{'='*40}")
    print(f"✅ Seeding complete!")
    print(f"   Resumes uploaded : {n_resumes}")
    print(f"   Jobs created     : {n_jobs}")
    print(f"\nNext steps:")
    print(f"  1. Open Streamlit UI: streamlit run ui/app.py")
    print(f"  2. Go to 'Results', select a job, click 'Run Ranking'")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    main()
