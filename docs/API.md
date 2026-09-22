# API

The public HTTP contract is versioned under `/api/v1`. OpenAPI is served by FastAPI at `/docs` when the API is running.

Errors use RFC 7807 `application/problem+json` (`type`, `title`, `status`, `detail`, `code`).

## Implemented

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Infrastructure liveness. `{ "status": "ok", "service": "api" }` |
| POST | `/api/v1/auth/register` | Candidate or recruiter self-registration. Returns a safe user DTO. Admin is rejected. |
| POST | `/api/v1/auth/login` | Email/password. Sets httpOnly refresh cookie. Returns access JWT + CSRF token + user DTO. |
| POST | `/api/v1/auth/refresh` | Cookie + CSRF/Origin. Rotates refresh session. Returns a new access JWT. |
| POST | `/api/v1/auth/logout` | Revokes current refresh session and clears cookies. |
| POST | `/api/v1/auth/logout-all` | Bearer access token. Revokes all refresh sessions for that user. |
| GET | `/api/v1/auth/me` | Bearer access token. Safe user DTO: `id`, `email`, `role`, `status`, `candidate_id`, `organization_id` (first membership). |
| POST | `/api/v1/candidates/{candidate_id}/resumes` | Multipart PDF/DOCX upload. Owner only. Returns metadata and parse status. |
| GET | `/api/v1/candidates/{candidate_id}/resumes` | Resume metadata list. Owner, or recruiter in candidate-visibility scope. |
| GET | `/api/v1/candidates/{candidate_id}/resumes/{resume_id}` | Resume metadata. Same authorization as list. No `storage_key`. |
| GET | `/api/v1/candidates/{candidate_id}/profile` | Owner only. Draft + confirmed profile views. |
| PUT | `/api/v1/candidates/{candidate_id}/profile` | Owner edits draft (does not touch confirmed rows). |
| POST | `/api/v1/candidates/{candidate_id}/profile/confirm` | Persists draft into profile item tables. |
| POST | `/api/v1/candidates/{candidate_id}/resumes/{resume_id}/extract` | Re-run NLP on a stored resume. |
| POST | `/api/v1/jobs` | Recruiter creates a job and runs JD NLP. |
| GET | `/api/v1/jobs` | Jobs in the recruiter's organization. |
| GET | `/api/v1/jobs/{job_id}` | Org-scoped job + latest requirements draft. |
| POST | `/api/v1/jobs/{job_id}/extract` | Re-run JD NLP. Confirmed requirements are not overwritten. |
| PUT | `/api/v1/jobs/{job_id}/requirements` | Recruiter edits the draft. |
| POST | `/api/v1/jobs/{job_id}/requirements/confirm` | Marks requirements authoritative and persists normalized job skills. |
| GET | `/api/v1/admin/ontology/skills` | Admin: list canonical skills. |
| POST | `/api/v1/admin/ontology/skills` | Admin: add a canonical skill (live catalog). |
| POST | `/api/v1/admin/ontology/aliases` | Admin: add an alias. |
| POST | `/api/v1/admin/ontology/relations` | Admin: add parent_of / related_to / similar_to. |
| GET | `/api/v1/admin/ontology/versions` | Admin: list ontology versions. |
| POST | `/api/v1/admin/ontology/versions` | Admin: snapshot live catalog as a new version. |
| GET | `/api/v1/admin/ontology/validation` | Admin: cycle/duplicate checks. |
| POST | `/api/v1/admin/ontology/seed` | Admin: idempotent CS/IT seed. |
| GET | `/api/v1/candidates/{candidate_id}/profile/embedding` | Owner: embedding status for the confirmed profile. No vector. |
| POST | `/api/v1/candidates/{candidate_id}/profile/embedding` | Owner: embed confirmed profile (`force=true` regenerates). |
| GET | `/api/v1/jobs/{job_id}/embedding` | Org recruiter: job embedding status. No vector. |
| POST | `/api/v1/jobs/{job_id}/embedding` | Org recruiter: embed confirmed job. |
| POST | `/api/v1/admin/embeddings/similarity` | Admin: cosine similarity of two compatible embeddings. Not a match score. |
| GET | `/api/v1/candidates/{candidate_id}/jobs` | Owner/admin: baseline current_match per visible job. Not a trained ranker. |
| GET | `/api/v1/candidates/{candidate_id}/jobs/{job_id}/match` | Owner, in-scope recruiter, or admin: detailed baseline match plus heuristic potential. |
| POST | `/api/v1/candidates/{candidate_id}/jobs/{job_id}/counterfactual` | Owner/admin: in-memory skill addition. Does not persist skills or a match run. |
| GET | `/api/v1/jobs/{job_id}/candidates` | Org recruiter: visible candidates, **baseline** `current_match DESC`. Not a trained ranker. Potential is shown; private career paths are not. Includes `current_decision`. |
| POST | `/api/v1/jobs/{job_id}/candidates/{candidate_id}/decisions` | Recruiter: append SHORTLIST/REJECT/REVIEW. Links the latest pre-decision feature snapshot. Does not train a model. |
| GET | `/api/v1/jobs/{job_id}/candidates/{candidate_id}/decisions` | Recruiter/admin: append-only history including private notes. Candidates: 403. |
| GET | `/api/v1/analytics/recruiter/overview` | Recruiter org: jobs, applications, shortlist/reject counts. Not a hire rate. |
| GET | `/api/v1/analytics/recruiter/skills` | Recruiter org: demand, supply, gaps. |
| GET | `/api/v1/analytics/recruiter/matching` | Recruiter org: score distributions. |
| GET | `/api/v1/analytics/recruiter/funnel` | Recruiter org: jobs → applications → reviewed → shortlisted → rejected. |
| GET | `/api/v1/analytics/admin/overview` | Admin: system-wide descriptive overview. |
| GET | `/api/v1/analytics/admin/skills` | Admin: system-wide skill demand/supply. |
| GET | `/api/v1/analytics/candidates/{candidate_id}/overview` | Owner/admin: that candidate's match distributions only. |
| POST | `/api/v1/admin/datasets/snapshots` | Admin: create a point-in-time dataset snapshot. Does not train. |
| GET | `/api/v1/admin/datasets/snapshots` | Admin: list snapshots. |
| GET | `/api/v1/admin/datasets/snapshots/{id}` | Admin: snapshot detail and training rows (no resume text, no recruiter notes). |
| GET | `/api/v1/admin/models` | Admin: candidate/active/rejected/retired models. No artifact filesystem paths. |
| GET | `/api/v1/admin/models/{id}` | Admin: evaluation, baseline comparison, activation eligibility. |
| POST | `/api/v1/admin/models/{id}/activate` | Admin: activate if artifact, schema, evaluation, and policy pass. Retires the previous active model. |
| POST | `/api/v1/admin/models/{id}/reject` | Admin: reject a non-active candidate. |
| GET | `/api/v1/candidates/{candidate_id}/career-paths` | Owner or admin: Suggested Skill Path. Optional `?job_id=`. Recruiters: 403. |

There is **no** `POST /api/v1/train`. Training is `python -m ml.train`.

Authorization **probes** (not recruitment features; used to enforce and test RBAC/tenancy):

| Method | Path | Rule |
|---|---|---|
| GET | `/api/v1/authz/candidate` | Role `candidate` |
| GET | `/api/v1/authz/recruiter` | Role `recruiter` |
| GET | `/api/v1/authz/admin` | Role `admin` |
| GET | `/api/v1/authz/candidates/{id}` | Candidate must own that row |
| GET | `/api/v1/authz/organizations/{id}` | Recruiter membership (admin allowed) |
| GET | `/api/v1/authz/jobs/{id}` | Job belongs to a membership org |
| GET | `/api/v1/authz/jobs/{id}/decisions` | Same org check; no decision payload yet |
| GET | `/api/v1/authz/candidates/{id}/recruiter-view` | Recruiter candidate-visibility policy |

This health endpoint does **not** report ML, ranking, or embedding status as a score. Embedding metadata is separate.

### Auth request/response notes

- Register body: `{ email, password, role: "candidate"|"recruiter", organization_name? }`. Recruiters must supply `organization_name` (creates an org; they become owner). Joining an existing org by id/slug is not public.
- Login/refresh JSON never includes the raw refresh token.
- Login failures: `401` generic `Invalid email or password.` Duplicate email: `409`. Validation: `422`. Authenticated but not allowed: `403`.
- Email is normalized to lowercase. Passwords are hashed with Argon2id.

### Resume notes

- Multipart field name: `file`. PDF (`application/pdf`) and DOCX only. Magic bytes are checked; extensions are not trusted.
- Upload/delete: candidate owner only. Recruiters cannot impersonate an upload.
- List/detail: owner, or recruiter/admin who passes the candidate-visibility policy. Metadata only (`filename`, MIME, size, parse status, parser version, timestamps). No filesystem paths.
- Parse statuses: `queued`, `processing`, `ready`, `failed`, `needs_ocr`.
- Errors: `400` invalid document, `413` too large, `415` unsupported type.
- Same candidate + same SHA-256: existing row is returned with `duplicate: true`. Different candidates get separate rows that may share a blob.

Frontend: keep the access token in memory; send it as `Authorization: Bearer`. Include `credentials: "include"` so the refresh cookie is sent. Cookie-authenticated POSTs should send `X-CSRF-Token` when the token is known; a trusted `Origin` is accepted after reload.

## Domain resources

SQLAlchemy models must not be returned from routers.

| Resource | Tables | Notes |
|---|---|---|
| Users / sessions | `users`, `refresh_sessions` | Email unique and lowercase. Refresh tokens stored as SHA-256 hashes. |
| Organizations | `organizations`, `organization_members` | Unique membership per (org, user). Recruiter access is membership-scoped. |
| Candidates | `candidates`, `candidate_profiles`, profile item tables, `candidate_skills` | Confirmed profile is the matching source of truth. Canonical skills written on confirm. |
| Resumes | `resumes`, `extraction_revisions` | Content-addressed blobs; HTTP implemented in Phase 3. `storage_key` is not unique (shared blob, separate authz rows). |
| Ontology | `skills`, `skill_aliases`, `skill_relations`, `ontology_versions` | Seeded CS/IT catalog. Admin HTTP only. Aliases are not skills. |
| Embeddings | `embeddings` | pgvector rows for confirmed profiles/jobs/chunks. No ranking. |
| Jobs | `jobs`, `job_requirements`, `job_required_skills`, `job_preferred_skills` | Create/extract/confirm HTTP is implemented. Canonical job skills are written on confirm. |
| Applications / decisions | `applications`, `candidate_decisions`, `recruiter_decisions` | Recruiter decision HTTP is implemented. Append-only. Notes are recruiter-private. |
| Matching audit | `match_runs`, `match_explanations`, `feature_snapshots`, `embeddings` | Baseline `current_match` is always persisted. `scoring_mode` is `baseline` or `trained`. `trained` requires `model_version`. |
| ML registry | `ml_models`, `ml_training_runs`, `dataset_snapshots` | Snapshots are immutable training input. Models start as `candidate`. Never auto-activated. Artifact paths are not exposed. |
| Ops | `processing_jobs`, `audit_logs` | Resume parse and resume NLP jobs are created in-process. No Redis/Celery worker. |

## Client rule

The Next.js app calls this API only. It does not connect to PostgreSQL and does not contain ranking weights or ML code. Replacing `RANKER_IMPL` later must not require frontend DTO changes for existing fields. Frontend route guards are not the security boundary.
