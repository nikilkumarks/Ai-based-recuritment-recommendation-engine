# ML training (Phase 10)

Recruiter shortlist/reject decisions are behavioral labels and are not ground-truth hiring outcomes.

No trained project model is produced until sufficient real labeled data exists.

This document is the Phase 10 training and serving contract. It does **not** report project accuracy. The current real labeled snapshot size is expected to be **3 eligible rows** (2 shortlist, 1 reject). `MIN_TRAINING_ROWS=50`, so the training CLI **must skip**.

## Target

Binary target: recruiter shortlist behavior.

| Label | Value | Included |
|---|---|---|
| SHORTLIST | 1 | Yes |
| REJECT | 0 | Yes |
| REVIEW | — | Excluded |
| No decision | — | Excluded |

This predicts **recruiter shortlist behavior**. It does **not** predict hiring, job performance, future success, candidate quality, human potential, or guaranteed selection.

The trained score is a **shortlist prediction score** / **model relevance score**: estimated probability of the observed recruiter shortlist label under this model. It is **not** a hire probability or success probability. Calibration is not claimed.

## Training entry points

Offline only. There is **no** `POST /api/v1/train`.

```bash
python -m ml.train --dataset <dataset_snapshot_id>
python -m ml.evaluate --dataset <dataset_snapshot_id>
```

If the snapshot is insufficient:

```
Training skipped:
insufficient real labeled data.
Insufficient real labeled data for training experiment.
```

No artifact is created. Active model state is not modified.

Optional `--register` writes `ml_training_runs` / `ml_models` only after a successful train. Skip does not activate anything.

## Pipeline

```
dataset snapshot (immutable)
  → validate dataset
  → point-in-time feature rows
  → feature validation
  → label validation
  → leakage checks
  → GroupKFold by job_id
  → baselines (random, exact skill overlap, deterministic current_match)
  → XGBoost (fold-wise scale_pos_weight from train fold only)
  → metrics (or unavailable)
  → candidate artifact + registry row
  → admin activate / reject
  → safe inference (or baseline fallback)
```

Training is read-only against `dataset_snapshots`, `feature_snapshots`, and `recruiter_decisions`.

## Feature schema

Serving/training vector: `ml-feature-schema-v1` with preprocessing `ml-preprocess-v1`.

Snapshot schemas `feature-schema-v1` and `feature-schema-v2` are accepted. v1 potential fields are transformed via the documented missing-value policy (`{name}__missing` flags; years fill `-1.0`; other nullable fills `0.0`). Incompatible schemas are rejected. Features are never silently reinterpreted.

Ordered predictive features (plus missing flags for nullable columns) include coverage, match counts, `profile_job_cosine`, `current_match`, experience/education/project evidence, and potential v2 closability signals. Exact names: `app/modules/features/schema.py` `FEATURE_NAMES`.

`job_id` is grouping metadata only. `candidate_id` is traceability only. Neither enters `X`.

## Forbidden features

Never used as predictors:

recruiter decision, decision reason, recruiter note, decision timestamp, `candidate_id`, `job_id`, `organization_id`, name, address, gender, religion, caste, race/ethnicity, disability, age, college prestige, raw resume text, raw JD text.

## Feature validation

Before training: expected names, numeric types, missing/infinite values, snapshot schema version, dimensions, ontology version, embedding identity. Invalid datasets are rejected. There is no silent arbitrary imputation. The missing-value policy is the same at train and serve time (`vectorize_features`).

## Data leakage

Automated checks fail training on future snapshots vs `decision_time`, forbidden keys in the feature payload, and ids/labels in the vector. Point-in-time Phase 9 linkage is required. Leakage ⇒ fail, no artifact.

## GroupKFold

Primary split is **GroupKFold by `job_id`**. The same job must not appear in both train and validation of a fold. Random row splitting is not the evaluation protocol.

Default 5 folds. If unique jobs `< 5`, folds reduce to `min(requested, n_jobs)` when `n_jobs >= 2`. If fewer than 2 jobs, training is refused. Folds are never fabricated.

## Class imbalance

Positive/negative counts and ratios are measured from the eligible rows. `scale_pos_weight` is `n_neg / n_pos` from the **training fold only** (and from the full eligible set only when fitting the final candidate artifact after CV). No synthetic balancing. No test-fold statistics.

## Baselines

Evaluated on the **same** held-out groups:

1. Random (uniform `[0,1]`, fixed seed; chance-level reference)
2. Exact skill overlap (`required_skill_coverage`)
3. Deterministic Phase 7 composer (`current_match`) — primary reference
4. XGBoost

The test fold is not used for hyperparameter search.

## XGBoost

`XGBClassifier`, conservative defaults: `n_estimators=80`, `max_depth=3`, `learning_rate=0.1`, `subsample=0.8`, `colsample_bytree=0.8`, `min_child_weight=1`, `reg_lambda=1.0`, `random_state=ML_RANDOM_SEED`, `n_jobs=1`. Configurable via settings. No large search.

## Metrics

Classification: ROC-AUC, PR-AUC, precision, recall, F1.

Ranking: Precision@K, Recall@K, NDCG@K for K in `{1,3,5,10}`.

If a metric is not mathematically valid for the evaluation data, the value is `null` with reason `insufficient_data`. Fake metrics are never emitted.

## Model version and artifact

Version example: `xgb-shortlist-v1-{utc}-{checksum}`. Identifies algorithm, dataset, feature schema, ontology versions, embedding identity, config, seed.

Artifacts live in `MODEL_ARTIFACT_DIR` (`ml/artifacts/` by default). Contents: `model.json`, `metadata.json` (schema, order, preprocess version, dataset id, timestamp, seed, evaluation, library versions). Large binaries are gitignored. Filesystem paths are never returned on public or admin JSON.

TEST FIXTURE ONLY artifacts are prefixed `test-fixture-only-` and must not be published as project performance.

## Registry and activation

`ml_training_runs` then `ml_models.status=candidate`. Statuses: `candidate | active | rejected | retired`. At most one `active`. Historical rows are not deleted. Activation is **never** automatic.

Admin HTTP only:

- `GET /api/v1/admin/models`
- `GET /api/v1/admin/models/{id}`
- `POST /api/v1/admin/models/{id}/activate`
- `POST /api/v1/admin/models/{id}/reject`

Activation requires: artifact exists, schema matches, evaluation exists, stored activation policy passes, not rejected. Previous active → `retired`.

Primary metric: `PRIMARY_METRIC=ndcg_at_5` (falls back to `roc_auc` if NDCG is unavailable). XGBoost must beat the deterministic baseline on the primary metric. A ROC-AUC drop greater than 0.10 vs baseline is a severe regression and blocks activation. There is no hardcoded “90% accuracy” rule.

Fixture-only models cannot be activated in `ENVIRONMENT=production`.

## Fallback and inference

If there is no active model, a missing/corrupt artifact, a schema mismatch, or incompatible ontology/embedding metadata: **baseline matching**. `scoring_mode=baseline`, `model_version=null`, internal `fallback_reason`. Recommendation requests do not crash.

When trained scoring succeeds: `scoring_mode=trained`, `model_version` set, `model_relevance_score` is the shortlist probability. Baseline `current_match` is always retained. The same model serves job→candidates and candidate→jobs.

The active artifact is loaded once per process and cached; it is reloaded if the active version changes.

## Explainability

SHAP (`TreeExplainer`) when the `shap` package works. Otherwise structured XGBoost `feature_importances_` labeled as importance, **not** as SHAP. No LLM prose. UI separates baseline traces from ML feature contributions:

“The trained model assigned a higher shortlist relevance score based on these features.”

## Minimum data

Refuse training unless all hold:

- `MIN_TRAINING_ROWS` (default 50)
- `MIN_POSITIVE_LABELS` (default 5)
- `MIN_NEGATIVE_LABELS` (default 5)
- `MIN_UNIQUE_JOBS` (default 2) and GroupKFold feasible

The exact reason is reported. Rows are never duplicated to meet the floor.

## Reproducibility

Recorded: dataset snapshot id, seed, XGBoost params, feature schema, preprocessing version, ontology versions, embedding identity, Python/numpy/sklearn/xgboost versions, timestamp. Same snapshot + config + seed should match as far as library/platform determinism allows.

## Limitations

- Recruiter labels are behavioral, not hiring outcomes.
- Scores are not calibrated hire probabilities.
- Small real datasets cannot support a project model or project metrics.
- TEST FIXTURE ONLY metrics are plumbing, not product performance.
- SHAP may be unavailable; importance is a fallback, not invented SHAP.
- GroupKFold with few jobs reduces fold count and ranking metrics may be `unavailable`.
