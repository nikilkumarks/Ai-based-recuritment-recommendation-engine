# Dataset construction (Phase 9/10)

**No trained project model is produced until sufficient real labeled data exists.**

Recruiter shortlist/reject decisions are behavioral labels and are not ground-truth hiring outcomes.

This document describes how recruiter decisions are stored, how they join to **pre-decision** feature snapshots, and how dataset snapshots are built. Phase 10 consumes a snapshot **read-only**. Training is skipped when `MIN_TRAINING_ROWS` (50) is not met. The current project test snapshot has 3 eligible rows. That skip is correct. Details: `docs/ML_TRAINING.md`.

## Pipeline

```
Candidate + Job
  → Baseline matcher (Phase 7/8)
  → Feature snapshot (immutable)
  → Match result
  → Recruiter decision (SHORTLIST / REJECT / optional REVIEW)
  → Decision label
  → Point-in-time dataset snapshot
  → Phase 10 offline training (`python -m ml.train`) when eligible
```

Training rows use the features that existed **before** the recruiter decision. Future profile, job, ontology, embedding, or score changes must not replace that snapshot.

## Recruiter decisions

Reuse table `recruiter_decisions` (append-only). Product actions:

| Action | Product | Binary training label |
|---|---|---|
| `shortlist` | Yes | Positive (`1`) |
| `reject` | Yes | Negative (`0`) |
| `review` | Optional | Unlabeled / excluded |
| `view` / `compare` / `hire` | Legacy CHECK only | Excluded. `hire` is not a product action. |

A shortlist is **not** a hire. A rejection is **not** proof that the candidate was objectively unqualified.

Each event stores: `id`, `recruiter_id`, `organization_id`, `job_id`, `candidate_id`, `action`, `created_at`, optional `reason`, optional `note`, `match_run_id`, `feature_snapshot_id`. Resume text, passwords, and tokens are never stored on decisions.

### Decision history vs current state vs training label

- **History:** every INSERT remains. Changing SHORTLIST → REJECT appends a new row.
- **Current state:** latest event by `(created_at ASC, id ASC)`.
- **Training label (`label-policy-v1`):** latest **binary** event (`shortlist` or `reject`) per `(candidate_id, job_id)`. `review` and no-decision rows are not negatives.

### Reasons

Optional recruiter-provided codes: `skill_gap`, `experience_gap`, `education_mismatch`, `strong_skill_match`, `strong_project_evidence`, `insufficient_evidence`, `other`.

`reason` is **not** inferred from the baseline model. Keep recruiter reasons separate from system explanations.

### Authorization

Recruiters may decide only when they belong to the job's organization and the candidate is in talent-pool scope. Candidates cannot create or list recruiter decisions (including private notes). Organization A cannot decide on Organization B's jobs. Admin may inspect history.

### Conflicts

If multiple recruiters record different binary actions, both events remain. The training label is still the latest binary event. The dataset row sets `decision_conflict=true`. No consensus is invented.

## Point-in-time feature selection

At decision INSERT time the service looks up:

```
feature_snapshots.created_at <= decision_time
for the same candidate_id and job_id
order by created_at DESC, id DESC
limit 1
```

That snapshot and its `match_run_id` are stored on the decision. Features are **not** regenerated after the decision.

If no prior snapshot exists, FKs stay null. The pair is **excluded** from the dataset until a valid pre-decision snapshot exists. Missing snapshots are not fabricated.

Tie-break: later `created_at` wins; if timestamps are equal, higher `id` wins. Snapshots with `created_at > decision_time` are never selected.

Historical `feature_snapshots` rows are immutable. Ontology, embedding, profile, job, and weight changes create **new** snapshots.

## Dataset snapshots

Admin `POST /api/v1/admin/datasets/snapshots` builds a new `dataset_snapshots` row. Existing snapshots are never overwritten. Names look like `dataset-v1-{utc}-{checksum8}-{entropy}`.

Each training row contains:

- grouping metadata: `candidate_id`, `job_id` (for GroupKFold by `job_id` in Phase 10; **not** predictive features)
- `label`, `decision_time`, `decision_id`, `decision_conflict`
- `feature_snapshot_id`, `match_run_id`
- `feature_schema_version`, `ontology_version`
- embedding identity: model name, version, dimensions, text version
- `features`: sanitized snapshot values (`current_match`, coverages, semantic similarity, potential fields when valid, …)

`MIN_TRAINING_ROWS` (default 50) is reported as `sufficient_for_training_experiment`. It does **not** start training and is not an accuracy claim.

Class balance (positives, negatives, ratios) is reported. Rows are not duplicated and negatives are not fabricated.

### Eligibility

A row is included only if all of the following hold:

- candidate and job exist via the decision FKs
- a recruiter decision exists
- latest eligible action is `shortlist` or `reject`
- a feature snapshot exists with `created_at <= decision_time`
- `feature_schema_version` is `feature-schema-v1` or `feature-schema-v2`
- ontology version is known
- if semantic features are marked available, embedding identity is present
- `current_match` is a finite value in `[0, 1]`; `potential` is null or in `[0, 1]`
- the label is not present in the feature vector

### Exclusion reasons

| Reason | Meaning |
|---|---|
| `no_decision` | Scored candidate-job pair with no recruiter decision |
| `review_unlabeled` | Latest non-binary action is `review` |
| `missing_feature_snapshot` | No snapshot at or before decision time |
| `feature_snapshot_after_decision` | Linked snapshot is in the future |
| `invalid_schema` | Unsupported feature schema |
| `unknown_ontology_version` | Ontology version missing |
| `unknown_embedding_identity` | Semantic features on, encoder identity missing |
| `invalid_feature_values` | Non-finite or out-of-range scores |
| `label_in_features` | Leakage guard |

## Leakage prevention

These must not appear in `features`:

- recruiter decision / shortlist / reject / review / hire / reason / note
- `label`
- future match runs or future snapshots
- protected attributes and obvious proxies: gender, religion, caste, race/ethnicity, disability, age, marital status, name, address, college prestige
- raw resume text, passwords, tokens

`job_id` is grouping metadata only. `decision_time` is for point-in-time construction, not a default model feature.

Dataset snapshots **reference** feature snapshots. They do not copy resume bytes or recruiter notes.

Baseline `current_match` and potential features are copied as they were at snapshot time. Recruiter labels do **not** retune baseline weights.

## Analytics

Descriptive SQL aggregations, organization-scoped for recruiters, own-data for candidates, system-wide for admin. Shortlist rate is not a hiring success rate. Hire rate is not shown because hire outcomes are not collected.

## Limitations

- Labels are recruiter behavior, not hiring outcomes.
- Talent-pool shortlists may exist without an `applications` row.
- `MIN_TRAINING_ROWS` is a reporting threshold only.
- Phase 10 must still choose splits (GroupKFold by `job_id`), handle imbalance, and evaluate against baselines before any model activation.
- No automatic retraining.
