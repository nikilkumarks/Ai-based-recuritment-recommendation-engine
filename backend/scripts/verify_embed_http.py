"""Live HTTP embedding flow against a running API. Not a ranking test."""

from __future__ import annotations

import time
import uuid

import httpx
from tests.fixtures.nlp_corpus import ANNOTATED_JD, ANNOTATED_RESUME
from tests.fixtures.resume_docs import pdf_with_lines

PASSWORD = "correct-horse-battery"
BASE = "http://127.0.0.1:8000"


def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    timeout = httpx.Timeout(300.0, connect=30.0)
    with httpx.Client(base_url=BASE, timeout=timeout, headers={"Origin": "http://localhost:3000"}) as client:
        unauth = client.post(f"/api/v1/candidates/{uuid.uuid4()}/profile/embedding")
        print("unauth_status", unauth.status_code)
        cand = client.post(
            "/api/v1/auth/register",
            json={"email": f"live-cand-{suffix}@example.com", "password": PASSWORD, "role": "candidate"},
        )
        assert cand.status_code == 201, cand.text
        login = client.post(
            "/api/v1/auth/login",
            json={"email": f"live-cand-{suffix}@example.com", "password": PASSWORD},
        )
        assert login.status_code == 200, login.text
        access = login.json()["access_token"]
        cid = login.json()["user"]["candidate_id"]
        auth = {"Authorization": f"Bearer {access}", "Origin": "http://localhost:3000"}

        draft_embed = client.post(f"/api/v1/candidates/{cid}/profile/embedding", headers=auth)
        print("unconfirmed_profile", draft_embed.status_code)

        lines = [line for line in ANNOTATED_RESUME.split("\n") if line.strip()]
        uploaded = client.post(
            f"/api/v1/candidates/{cid}/resumes",
            headers=auth,
            files={"file": ("cv.pdf", pdf_with_lines(lines), "application/pdf")},
        )
        assert uploaded.status_code == 201, uploaded.text
        confirmed = client.post(f"/api/v1/candidates/{cid}/profile/confirm", headers=auth)
        assert confirmed.status_code == 200, confirmed.text

        started = time.perf_counter()
        embedded = client.post(f"/api/v1/candidates/{cid}/profile/embedding", headers=auth)
        print("candidate_embed_ms", int((time.perf_counter() - started) * 1000))
        assert embedded.status_code == 200, embedded.text
        body = embedded.json()
        print("candidate_status", body["status"])
        print("candidate_dim", body["dimensions"])
        print("candidate_model", body["model_name"])
        print("candidate_hash", body["content_hash"])
        print("candidate_has_vector", "vector" in body)
        status = client.get(f"/api/v1/candidates/{cid}/profile/embedding", headers=auth)
        print("candidate_get_status", status.json()["status"])
        print("candidate_get_has_vector", "vector" in status.json())

        rec = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"live-rec-{suffix}@example.com",
                "password": PASSWORD,
                "role": "recruiter",
                "organization_name": f"Live Org {suffix}",
            },
        )
        assert rec.status_code == 201, rec.text
        rec_login = client.post(
            "/api/v1/auth/login",
            json={"email": f"live-rec-{suffix}@example.com", "password": PASSWORD},
        )
        rec_auth = {
            "Authorization": f"Bearer {rec_login.json()['access_token']}",
            "Origin": "http://localhost:3000",
        }
        job = client.post(
            "/api/v1/jobs",
            headers=rec_auth,
            json={"title": "Backend Engineer", "description_raw": ANNOTATED_JD},
        )
        assert job.status_code == 201, job.text
        job_id = job.json()["id"]
        unconfirmed_job = client.post(f"/api/v1/jobs/{job_id}/embedding", headers=rec_auth)
        print("unconfirmed_job", unconfirmed_job.status_code)
        confirmed_job = client.post(f"/api/v1/jobs/{job_id}/requirements/confirm", headers=rec_auth)
        assert confirmed_job.status_code == 200, confirmed_job.text
        job_embed = client.post(f"/api/v1/jobs/{job_id}/embedding", headers=rec_auth)
        assert job_embed.status_code == 200, job_embed.text
        print("job_status", job_embed.json()["status"])
        print("job_dim", job_embed.json()["dimensions"])
        print("job_model", job_embed.json()["model_name"])
        print("job_has_vector", "vector" in job_embed.json())
        job_get = client.get(f"/api/v1/jobs/{job_id}/embedding", headers=rec_auth)
        print("job_get_status", job_get.json()["status"])
        print("job_get_has_vector", "vector" in job_get.json())


if __name__ == "__main__":
    main()
