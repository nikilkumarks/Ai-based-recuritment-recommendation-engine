# Security

PRJ_385 is a **college-project deployment**, not a production internet-hardened service. Controls below are real and enforced in code, but they are sized for a lab/Docker Compose viva — not for a public multi-tenant SaaS.

## 1. Authentication

Email + password. Passwords are hashed with **Argon2id** before insert. Login failures use a generic message so callers cannot tell whether an email exists.

Short-lived **JWT access tokens** (default 15 minutes) carry `sub`, `role`, `iat`, `exp`, `jti`, and `typ=access`. They do not carry passwords, profiles, resume data, or authorization decisions. Every authenticated request reloads the user from PostgreSQL; a stale JWT role is not enough for a mutation.

**Refresh sessions** live in `refresh_sessions`. Only `token_hash` (SHA-256 of the raw token) is stored. Raw refresh tokens are httpOnly cookies, never JSON. Refresh **rotates** the token and revokes the previous row. Reuse of a rotated token revokes the whole session family.

`logout` revokes the current session and clears cookies. `logout-all` revokes every active session for that user (requires a valid access token).

Suspended users cannot log in or use authenticated endpoints. Accounts are not deleted to implement suspension.

Admin accounts cannot be self-registered.

## 2. Authorization

FastAPI is the security boundary. Next.js route groups and `session_hint` cookies are UX only and can be forged.

| Role | Server-side rule |
|---|---|
| Candidate | Own candidate row, own resumes. Never another candidate. |
| Recruiter | Organizations they belong to; jobs of those orgs; in-scope candidate **metadata** (not resume files). |
| Admin | System probes and later admin APIs. Created only by trusted persistence, not a public endpoint. |

Resource IDs in URLs are untrusted. Dependencies: `get_current_active_user`, `require_role`, `require_candidate_owner`, `require_org_member`.

Candidate visibility is a **policy**, default `applicants_and_opted_in` (applicants to the recruiter's org jobs, plus `preferences.discoverable`). Modes `applicants_only` and `shared_campus_pool` exist because the campus vs org-private pool decision is still open.

## 3. Token storage

| Token | Storage |
|---|---|
| Access JWT | Frontend **memory** (React state). Not localStorage. |
| Refresh token | httpOnly cookie, path `/api/v1/auth`, SameSite configurable (default Lax), Secure in production. |
| CSRF token | Returned in login/refresh JSON; also a non-httpOnly cookie on the API host. |
| UX role hint | `session_hint` cookie set by the browser for Next.js middleware. Not a credential. |

## 4. Password hashing

Argon2id via `argon2-cffi`. Plaintext passwords are never persisted, logged, or returned. Login verifies against a dummy hash when the email is unknown to reduce timing signal.

Minimum length 8. Rejects empty/whitespace-padded secrets, password==email, single-character repeats, and a small common-password list. No mandatory composition rules.

## 5. CSRF

Refresh and logout authenticate with cookies, so CSRF applies.

1. **Origin allowlist** — if `Origin` is present it must be in `CORS_ORIGINS`. A trusted Origin on a credentialed CORS POST is accepted without a CSRF header so the SPA can refresh after a full reload (access token and CSRF are in memory only).
2. **CSRF header** — `X-CSRF-Token` is required when Origin is absent (non-browser clients). If the header is sent, it must match the hash stored on the refresh session.
3. **SameSite** on the refresh cookie (default Lax).

httpOnly does **not** prevent CSRF by itself.

Bearer access-token routes are not cookie-CSRF endpoints; browsers cannot attach `Authorization` from a foreign form post.

## 6. CORS

Configured from `CORS_ORIGINS`. Credentials are enabled. `allow_origins=["*"]` is not used. Development: `http://localhost:3000` and `http://127.0.0.1:3000` → API `http://localhost:8000`.

## 7. Rate limiting

Login, register, and refresh are rate-limited per client IP.

Implementation: in-memory sliding window (`InMemoryRateLimiter`). **Limitation:** counts are per process, not shared across API replicas, and reset on restart. Redis can replace the interface later. This is not sufficient for a public internet deployment.

Disable with `RATE_LIMIT_ENABLED=false` in tests.

## 8. PII handling

APIs return `id`, `email`, `role`, `status`, and `candidate_id` for the current user. They do not return password hashes, refresh tokens, session metadata, storage paths, or resume file contents.

Do not log passwords, tokens, or resume text. Audit metadata is limited to role, reason codes, and similar non-secret fields.

## 9. Resume upload controls

Uploads are PDF/DOCX only. The API checks declared MIME type and magic bytes; filename extensions are not trusted. Empty files, oversized files (`MAX_RESUME_BYTES`), path-traversal names, and mismatched signatures are rejected. Blobs are stored under `BLOB_ROOT/resumes/<sha256>` — client paths never become filesystem paths. `storage_key` is not returned to clients.

Malware scanning is **not implemented**. That is a deployment limitation, not a scanner integration.

## 10. Audit logging

`audit_logs` records: `auth.register`, `auth.login_success`, `auth.login_failure`, `auth.refresh`, `auth.logout`, `auth.logout_all`, `authz.denied`, `resume_uploaded`, `resume_parse_started`, `resume_parse_completed`, `resume_parse_failed`, `resume_deleted`. Actor id is set when known. Login failure for a missing email does not include the email address. Resume audits store checksum/MIME/status only — never file bytes or extracted text.

## 11. Known limitations

- College-project / lab deployment. Default JWT secret is for local development only; production must set `JWT_SECRET`.
- In-memory rate limiting does not coordinate across instances.
- No email verification, password reset, MFA, or OAuth.
- No brute-force lockout beyond rate limits.
- `session_hint` is forgeable; only the API is authoritative.
- Candidate pool policy is configurable and not a final product decision.
- No virus scanning, WAF, or bot management. Resume malware scanning is not implemented.
- Local disk blob storage (`BLOB_ROOT`); not S3. Fine for lab Compose, not a multi-node production store.
- OCR is not implemented. Textless PDFs are marked `needs_ocr`.
- Document parsing runs in-process (no Redis/Celery worker).
- Refresh cookie `Secure` is off in local HTTP; Compose/production should set `COOKIE_SECURE=true` behind HTTPS.
- Argon2 parameters are reduced in tests (`ARGON2_TIME_COST=1`); do not copy test parameters into production.
