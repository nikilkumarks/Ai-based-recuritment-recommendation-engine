from __future__ import annotations

from fastapi.testclient import TestClient

from tests.auth_helpers import login_user, register_user
from tests.fixtures.nlp_corpus import ANNOTATED_JD


def _recruiter(client: TestClient, email: str, org: str):
    register_user(client, email=email, role="recruiter", organization_name=org)
    tokens = login_user(client, email=email)
    return tokens["_access"], tokens["user"]


def test_job_extraction_and_confirm(client: TestClient) -> None:
    token, user = _recruiter(client, "jd-owner@example.com", "Nlp Corp")
    created = client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Backend Engineer", "description_raw": ANNOTATED_JD},
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    req = created.json()["requirements"]
    assert req is not None
    assert req["draft"]["nlp_pipeline_version"] == "nlp-v1"
    skills = [item["raw_text"].casefold() for item in req["draft"]["required_skills"]]
    assert "python" in skills
    edited = client.put(
        f"/api/v1/jobs/{job_id}/requirements",
        headers={"Authorization": f"Bearer {token}"},
        json={"location": "Hyderabad"},
    )
    assert edited.status_code == 200
    confirmed = client.post(
        f"/api/v1/jobs/{job_id}/requirements/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmation_status"] == "confirmed"
    detail = client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.json()["location"] == "Hyderabad"
    assert user.get("organization_id")


def test_recruiter_cannot_access_foreign_job(client: TestClient) -> None:
    token_a, _ = _recruiter(client, "jd-a@example.com", "Org A NLP")
    token_b, _ = _recruiter(client, "jd-b@example.com", "Org B NLP")
    created = client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"title": "Backend Engineer", "description_raw": ANNOTATED_JD},
    )
    job_id = created.json()["id"]
    denied = client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert denied.status_code == 403
    denied_edit = client.put(
        f"/api/v1/jobs/{job_id}/requirements",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"location": "Nowhere"},
    )
    assert denied_edit.status_code == 403
