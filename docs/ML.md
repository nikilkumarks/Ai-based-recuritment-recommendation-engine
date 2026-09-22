# ML decisions

**Status: Phase 10 training pipeline is implemented.** Phase 7 added an interpretable baseline composer. Phase 8 added a **deterministic potential heuristic** for gap closability. Phase 9 collects recruiter SHORTLIST/REJECT labels and builds point-in-time dataset snapshots. Phase 10 trains XGBoost **only** when a snapshot meets `MIN_TRAINING_ROWS` and class/group floors. **No trained project model is produced until sufficient real labeled data exists.** Potential is not a probability of hiring, selection, or future performance. Phase 6 embeddings provide semantic similarity features. They do not produce the final recruitment score.

Recruiter shortlist/reject decisions are behavioral labels and are not ground-truth hiring outcomes.

See `docs/ML_TRAINING.md` for the training contract, activation policy, fallback, and metric rules.

That is not an excuse to show cosine similarity as "87% Match". Fake labels, invented accuracy, and automatic retraining are forbidden. Training is offline (`python -m ml.train`). There is no public training HTTP endpoint.

NLP extraction is not semantic skill normalization. Skill normalization is not candidate-job matching. Embedding similarity is a third evidence source and must not write canonical skills.

See `docs/DATASET.md` for label policy, point-in-time joins, exclusion rules, and leakage prevention.

## Embeddings (Phase 6)

- Model name: `sentence-transformers/all-MiniLM-L6-v2` (configurable)
- Application model version: `all-minilm-l6-v2-v1` (not a Hugging Face SHA)
- Upstream revision: optional `EMBEDDING_MODEL_REVISION`; empty = library default, not a claimed SHA
- Dimension: read from the loaded encoder (384 for MiniLM-L6-v2). Stored length must match. Never pad/truncate.
- Text version: `embedding-text-v1` (builder is authoritative; settings must match)
- Storage: existing `embeddings.vector` (pgvector), plus `embedding_text_version` and `chunk_type` from Alembic `0006`
- Test-only hashing encoder identity: `hashing-encoder` / `hashing-v1` (8-d). Production Docker installs `sentence-transformers`.
- Privacy: source text and raw vectors are not logged and not returned to candidates/recruiters

Phase 1 added **empty** persistence for future training. Phase 10 writes `ml_training_runs` and `ml_models` only when a real (or TEST FIXTURE ONLY) train succeeds. Skip-on-insufficient-data does not create a project model. Nothing is auto-activated.

## Persistence now in PostgreSQL

- `feature_snapshots` — frozen inference feature JSON keyed to a `match_run`. Immutable after insert.
- `recruiter_decisions` — append-only recruiter actions (`shortlist|reject|review`, plus legacy view/compare/hire). Behavioral labels, not hiring outcomes.
- `dataset_snapshots` — point-in-time training-row payloads and manifests. Training consumes them read-only.
- `ml_models` / `ml_training_runs` — registry and run audit. Statuses: candidate, active, rejected, retired. At most one active model.

## Dataset

Source: recruiter `shortlist` / `reject` joined to the latest **pre-decision** feature snapshot. Versioned snapshots (`dataset-v1-…`). Details: `docs/DATASET.md`.

Do not invent a dataset or commit synthetic “accuracy.”

## Target variable

Initial binary target (`label-policy-v1`): P(recruiter shortlist) approximated as shortlist=1, reject=0. This is **not** P(hire). `review` and no-decision are unlabeled.

## Labels

- SHORTLIST = positive
- REJECT = negative
- REVIEW = unlabeled / excluded
- No decision = excluded (not a rejection)

Latest binary decision per `(candidate_id, job_id)` is the training label. Full event history is retained. Conflicting recruiters set `decision_conflict=true`; no consensus is invented.

## Features

Serving uses versioned `feature-schema-v1` fields for current match (see `docs/MATCHING.md`). Snapshots persist `feature-schema-v2` so potential features can be stored without changing v1 meanings. Dataset rows keep `feature_schema_version`, `ontology_version`, and embedding identity. `job_id` is grouping metadata, not a predictive feature. Protected attributes and recruiter notes are excluded. No XGBoost training is implemented. Potential features are heuristic closability signals, not labels.

## Train / validation / test strategy

**GroupKFold by `job_id`**. Random row splitting is not the primary evaluation. Details: `docs/ML_TRAINING.md`.

## Baselines

Required before activating any trained model:

1. Random ranker
2. Exact skill-overlap ranker
3. Interpretable weighted current-match composer (no XGBoost)

A model that loses to these baselines on a held-out set must not be activated.

## Evaluation metrics

ROC-AUC, PR-AUC, precision, recall, F1, Precision@K / Recall@K / NDCG@K for K in 1,3,5,10. If invalid for the data: `null` / `insufficient_data`. **No project performance metrics exist until a real snapshot meets the training floors.** Fixture metrics are TEST FIXTURE ONLY.

## Model versions

Registry table `ml_models` (`status = candidate | active | rejected | retired`). At most one row may be `active`. Artifacts in `MODEL_ARTIFACT_DIR`. Serving falls back to baseline when no compatible active model exists. No project model is trained until sufficient real labeled data exists.

## Reproducibility

Each training run records seed, ontology versions, embedding identity, feature schema, hyperparameters, dataset snapshot id, and library versions. Same snapshot + config + seed should reproduce as far as library/platform determinism allows.
