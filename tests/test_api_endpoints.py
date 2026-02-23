"""
tests/test_api_endpoints.py — Integration tests for FastAPI endpoints.

Uses FastAPI TestClient (synchronous httpx client under the hood).
Tests run against an in-memory DB, bypassing the real database.
"""

import json
import pytest  # type: ignore
from fastapi.testclient import TestClient  # type: ignore
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# We patch the DB dependency and model loading so tests don't need
# real files or the 80MB embedding model.
# ---------------------------------------------------------------------------

def _make_test_app(test_db):
    """Create app with DB dependency overridden to use in-memory test DB."""
    import app.api.main as main_mod  # type: ignore
    app = main_mod.app
    import app.api.dependencies as deps  # type: ignore
    get_db = deps.get_db

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(test_db):
    """Create a TestClient backed by in-memory DB and mocked embedding model."""
    import numpy as np  # type: ignore
    with patch("app.services.embedding_service.get_embedding_service") as mock_emb:
        mock_svc = MagicMock()
        mock_svc.add_resume.return_value = None
        mock_svc.remove_resume.return_value = None
        mock_svc.get_resume_embedding.return_value = np.zeros(384)
        mock_svc.get_jd_embedding.return_value = np.zeros(384)
        mock_svc.cosine_similarity.return_value = 0.65
        mock_svc.encode.return_value = np.zeros((1, 384))
        mock_emb.return_value = mock_svc

        app = _make_test_app(test_db)
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestResumeEndpoints:
    def test_upload_text_resume(self, client):
        resp = client.post(
            "/resumes/upload-text",
            data={"name": "Test Candidate", "raw_text":
                  "Python developer with 5 years experience. Skills: Python, SQL, Docker."}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "resume_id" in data
        assert data["candidate_name"] == "Test Candidate"

    def test_list_resumes_empty(self, client):
        resp = client.get("/resumes/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_get_resume_after_upload(self, client):
        # Upload first
        client.post("/resumes/upload-text",
                    data={"name": "Jane", "raw_text": "Python developer 3 years. Skills: Python."})
        # List and get id
        listed = client.get("/resumes/").json()
        assert listed["total"] >= 1
        rid = listed["resumes"][0]["id"]

        resp = client.get(f"/resumes/{rid}")
        assert resp.status_code == 200
        assert "parsed" in resp.json()

    def test_get_nonexistent_resume(self, client):
        resp = client.get("/resumes/99999")
        assert resp.status_code == 404

    def test_delete_resume(self, client):
        client.post("/resumes/upload-text",
                    data={"name": "To Delete", "raw_text": "Python developer."})
        listed = client.get("/resumes/").json()
        rid = listed["resumes"][0]["id"]

        del_resp = client.delete(f"/resumes/{rid}")
        assert del_resp.status_code == 204

        get_resp = client.get(f"/resumes/{rid}")
        assert get_resp.status_code == 404


class TestJobEndpoints:
    def test_create_job(self, client):
        resp = client.post("/jobs/", json={
            "title": "ML Engineer",
            "description": (
                "We need a senior ML engineer.\n\nRequired Skills:\n- Python\n- Machine Learning\n"
                "- Docker\n\nRequirements:\nMinimum 3 years of experience in ML."
            )
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "job_id" in data
        assert data["title"] == "ML Engineer"

    def test_list_jobs(self, client):
        client.post("/jobs/", json={
            "title": "Data Analyst",
            "description": "We need a data analyst with SQL and Python skills. "
                           "Required: SQL, Python, Excel. 2 years experience required."
        })
        resp = client.get("/jobs/")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_get_job_detail(self, client):
        created = client.post("/jobs/", json={
            "title": "Test Job",
            "description": "Python developer with SQL skills required. "
                           "Required Skills: Python, SQL. 1 year experience required."
        }).json()
        job_id = created["job_id"]
        resp = client.get(f"/jobs/{job_id}")
        assert resp.status_code == 200
        assert "current_weights" in resp.json()

    def test_get_nonexistent_job(self, client):
        resp = client.get("/jobs/99999")
        assert resp.status_code == 404


class TestRankingEndpoints:
    def test_ranking_no_resumes_returns_422(self, client):
        job = client.post("/jobs/", json={
            "title": "Dev Role",
            "description": "Python developer needed. Required: Python, SQL. 2 years experience."
        }).json()
        resp = client.post(f"/rank/{job['job_id']}")
        assert resp.status_code == 422  # no resumes

    def test_ranking_with_resumes(self, client):
        # Create job
        job = client.post("/jobs/", json={
            "title": "ML Role",
            "description": "ML Engineer needed. Required: Python, Machine Learning. 3 years experience required."
        }).json()
        # Upload resume
        client.post("/resumes/upload-text", data={
            "name": "ML Expert",
            "raw_text": "Senior ML Engineer. 5 years experience. Skills: Python, Machine Learning, Docker."
        })
        # Rank
        resp = client.post(f"/rank/{job['job_id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert "ranked_candidates" in data
        assert len(data["ranked_candidates"]) >= 1
        assert data["ranked_candidates"][0]["rank"] == 1

    def test_results_endpoint_after_ranking(self, client):
        job = client.post("/jobs/", json={
            "title": "Test Role",
            "description": "Python developer needed. Required: Python. 1 year experience."
        }).json()
        client.post("/resumes/upload-text", data={
            "name": "Dev", "raw_text": "Python developer 2 years. Skills: Python, SQL."
        })
        client.post(f"/rank/{job['job_id']}")
        resp = client.get(f"/rank/{job['job_id']}/results")
        assert resp.status_code == 200
        assert len(resp.json()["ranked_candidates"]) >= 1
