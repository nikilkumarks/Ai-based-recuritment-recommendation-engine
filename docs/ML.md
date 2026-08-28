# ML decisions

**Status: not finalized for training.** Phase 7 added an interpretable baseline composer. **The baseline composer is an interpretable reference system. It is not a trained ML model and its weights are heuristic until validated against labeled data.** Phase 6 embeddings provide semantic similarity features. They do not produce the final recruitment score.

That is not an ML model, not a ranker, and not XGBoost. Cosine similarity must not be shown as "87% Match".

NLP extraction is not semantic skill normalization. Skill normalization is not candidate-job matching. Embedding similarity is a third evidence source and must not write canonical skills.

## Embeddings (Phase 6)

- Model name: `sentence-transformers/all-MiniLM-L6-v2` (configurable)
- Application model version: `all-minilm-l6-v2-v1` (not a Hugging Face SHA)
- Upstream revision: optional `EMBEDDING_MODEL_REVISION`; empty = library default, not a claimed SHA
- Dimension: read from the loaded encoder (384 for MiniLM-L6-v2). Stored length must match. Never pad/truncate.
- Text version: `embedding-text-v1` (builder is authoritative; settings must match)
- Storage: existing `embeddings.vector` (pgvector), plus `embedding_text_version` and `chunk_type` from Alembic `0006`
- Test-only hashing encoder identity: `hashing-encoder` / `hashing-v1` (8-d). Production Docker installs `sentence-transformers`.
- Privacy: source text and raw vectors are not logged and not returned to candidates/recruiters

Phase 1 added **empty** persistence for future training. Nothing in `ml_models` is a result, a metric, or a label policy.

## Persistence now in PostgreSQL

- `feature_snapshots` — frozen inference feature JSON keyed to a `match_run`. Empty until matching exists.
- `recruiter_decisions` — view/compare/shortlist/reject/hire actions. **Not labeled** as positive or negative yet.
- `dataset_snapshots` — registry of future training sets. No rows required. No dataset is assumed to exist.
- `ml_models` / `ml_training_runs` — registry and run audit. Status `candidate|active|retired`. No artifacts. No metrics.

## Dataset

Not selected. Candidates (none assumed to exist in-repo):

- Product labels from recruiter shortlist/reject (after that UI exists)
- Team-annotated gold pairs
- Licensed public data (ESCO/O*NET or similar) after a license check

Do not invent a dataset or commit synthetic “accuracy.”

## Target variable

Not selected. Options discussed in architecture: P(shortlist), P(hire), expert grade, pairwise preference.

## Labels

Not defined. Decide what counts as a positive, what is a true negative, and what is unknown (e.g. viewed but not shortlisted). Recruiter decision rows are **not** automatically labels.

## Features

Serving uses versioned `feature-schema-v1` (see `docs/MATCHING.md`). Snapshots store the exact values used at inference time on `feature_snapshots`. No XGBoost training is implemented. Potential is not a feature yet.

## Train / validation / test strategy

Not selected. Architecture recommendation: **GroupKFold by `job_id`**, point-in-time features (no post-decision leakage). Confirm before the first reported experiment.

## Baselines

Required before activating any trained model:

1. Random ranker
2. Exact skill-overlap ranker
3. Interpretable weighted current-match composer (no XGBoost)

A model that loses to these baselines on a held-out set must not be activated.

## Evaluation metrics

Not selected. **No ML metrics exist yet.** Depends on the target (ROC/PR-AUC, precision/recall@k, NDCG@k, etc.).

## Model versions

Registry table `ml_models` exists (`status = candidate | active | retired`). At most one row may be `active`. `RANKER_IMPL=baseline` until an artifact is evaluated and activated. No model has been trained.

## Reproducibility

Each future training run must record git SHA, ontology version, embedding model name, feature schema version, hyperparameters, and data snapshot id. Not applicable until a dataset exists.
