# PRJ_385 — AI-Based Recruitment Recommendation Engine

## Project

PRJ_385 — AI-Based Recruitment Recommendation Engine

## Domain

Machine Learning + Analytics

## SDG

SDG 9 — Industry, Innovation and Infrastructure

## Vision

Traditional ATS tools score resumes by exact keyword overlap. This project is built to understand **skill meaning and structure**: aliases (`ML` = Machine Learning), hierarchy (Deep Learning under Machine Learning under AI), related skills, projects, experience, and **candidate potential** — then explain the result with structured traces rather than a black-box score.

An LLM is **not** the recommendation model. NLP, ontology matching, embeddings, a trainable tabular model (XGBoost, later), and ranking are separate layers.

## Current Status

**Phase 7 — Baseline matching.** Deterministic, interpretable current_match (0.0–1.0) from ontology evidence, stored embeddings, and configurable heuristic weights. Not a trained model, not ranking, not accuracy. `potential` remains null.

- No trained ML model
- No final dataset
- No production recommendation model
- No fake metrics, scores, or placeholder ranking logic

The running system is a Next.js UI with login/register, candidate resume upload, profile draft review at http://localhost:3000/candidate/profile, recruiter jobs at http://localhost:3000/recruiter/jobs, a FastAPI auth/documents/NLP API, and PostgreSQL 16 with pgvector. See `docs/SECURITY.md`.

## Architecture

```
Next.js (candidate / recruiter / admin)
        │  HTTP JSON  /api/v1
        ▼
FastAPI modular monolith
        │
        ├── NLP            extracts information from documents
        ├── Ontology       normalizes skills; aliases, hierarchy, relatedness
        ├── Embeddings     semantic similarity (frozen encoder)
        ├── Matching       deterministic skill/requirement comparison
        ├── ML             learns from engineered features (when labels exist)
        ├── Ranking        orders candidates or jobs
        └── Explainability structured traces (not generated prose)
        │
        ▼
PostgreSQL 16 + pgvector
```

Frontend never talks to Postgres, never loads model weights, and never contains ranking weights. `RANKER_IMPL` can switch from `baseline` to a trained artifact without changing the public DTO contract.

## Local Development

Prerequisites: Docker Desktop. PostgreSQL is **not** assumed to be running on the host. Start the Compose stack first.

```bash
copy .env.example .env
docker compose up --build
```

Wait until Postgres is healthy, then apply migrations:

```bash
docker compose exec -T -e PYTHONPATH=/app backend alembic upgrade head
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API health | http://localhost:8000/api/v1/health |
| OpenAPI | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 (user/password/db: `recs`) |

The API image installs `sentence-transformers` and loads `sentence-transformers/all-MiniLM-L6-v2` locally. Production `EMBEDDING_BACKEND` is `sentence_transformers`. `hashing` is for unit tests only and must not be used as MiniLM.

Optional ontology seed (skills/aliases/edges only; repeatable; no fake users or scores):

```bash
python scripts/seed_ontology.py
```

Host-side tests (optional):

```bash
cd backend
pip install -e ".[dev]"
pytest
ruff check .

cd ../frontend
npm install
npm run lint
npm run typecheck
npm test
npm run build
```

## Repository layout

```
frontend/    Next.js App Router
backend/     FastAPI modular monolith
ml/          Offline train/eval (not implemented)
ontology/    Seed graph (empty until ontology phase)
docs/        Architecture, API, ontology, ML, matching decisions
storage/     Uploaded files (gitignored)
```

## What not to add yet

Ranking, XGBoost, career path, analytics, or hardcoded recommendation scores. Those belong to later phases. Baseline matching is implemented and is not a trained model. Embeddings provide semantic similarity features; they are not a recruitment score. Security notes: `docs/SECURITY.md`.
