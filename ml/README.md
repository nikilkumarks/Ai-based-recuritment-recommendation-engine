# ML package (offline)

Training and evaluation for PRJ_385 live here, **not** in FastAPI request handlers.

## Phase 0 status

- No dataset
- No labels
- No trained model
- `ml/artifacts/` is gitignored
- `python -m ml.train` and `python -m ml.evaluate` exit with an explanation

## Rules

- Do not depend on HTTP requests.
- Do not commit weights or metrics files.
- Do not report accuracy until `docs/ML.md` decisions are finalized and evaluation has run against a real held-out set.
- Serving inference will load an **activated** artifact from the model registry in a later phase. Swapping `RANKER_IMPL` must not change the frontend DTO contract.
