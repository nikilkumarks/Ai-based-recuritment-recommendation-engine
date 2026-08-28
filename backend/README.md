# PRJ_385 API

FastAPI modular monolith for the AI-Based Recruitment Recommendation Engine.

Phase 2 exposes authentication under `/api/v1/auth` plus `/api/v1/health`. Domain modules other than identity/authorization remain empty of business features.

## Dependency rules

- Routers call services. Routers stay thin.
- Services hold application logic. Repositories hold database access.
- `app.modules.nlp` must not import `app.modules.ml`.
- `app.modules.ml` must not import FastAPI.
- `app.modules.matching` must not import `app.modules.ranking`.
- Training lives in `/ml` at the repo root and must not call HTTP APIs.

## Local (without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
pytest
ruff check .
```

Requires PostgreSQL with pgvector. Start the stack with `docker compose up --build`, then:

```bash
docker compose exec -T -e PYTHONPATH=/app backend alembic upgrade head
```

Production embeddings use `sentence-transformers` (`EMBEDDING_BACKEND=sentence_transformers`). The hashing encoder is for unit tests only and uses identity `hashing-encoder`, never MiniLM metadata.
