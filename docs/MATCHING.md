# Matching — baseline composer

**Status: Phase 7 implemented.** The baseline composer is an interpretable reference system. It is not a trained ML model and its weights are heuristic until validated against labeled data.

This document is the contract for candidate–job **current match**. Potential, ranking, and XGBoost are out of scope.

## Philosophy

Current match answers: *how well does the confirmed candidate currently satisfy the confirmed job requirements?*

It is:

- deterministic
- interpretable
- reproducible from stored features + scoring policy
- independent of XGBoost and of any trained ranker

It is **not** accuracy, precision, recall, NDCG, or an “AI score.” Cosine similarity is a feature, not the match score.

Potential (gap closability) is **not calculated**. `potential` is always `null`. `scoring_mode` is always `baseline`. `model_version` is always `null`.

## Architecture

```
Confirmed profile → canonical skills → ontology → candidate embedding
Confirmed job     → canonical required/preferred skills → job embedding
        ↓
Match orchestrator
        ↓
Feature extraction (feature-schema-v1)
        ↓
Baseline composer (weighted, configurable)
        ↓
Explanation traces + gaps
        ↓
MatchResult DTO
        ↓
match_runs + feature_snapshots + match_explanations
```

The same composer scores **candidate → jobs** and **job → candidates**. Only authorization and the filtered set change.

Matching may consume ontology, embeddings, candidates, and jobs. It must not import `ml` or `ranking`.

## Feature schema (`feature-schema-v1`)

Every snapshot includes `feature_schema_version`, `candidate_id`, `job_id`, `created_at`, `ontology_version`, embedding identity (model/name/version/dimensions/text version), and the feature values below. Feature meanings must not change silently; bump the schema version instead.

### Skill features

| Feature | Meaning |
|---|---|
| `required_skill_count` | Distinct canonical required skills |
| `matched_required_skill_count` | Required skills with **exact** canonical/alias evidence |
| `partial_required_skill_count` | Required skills whose best evidence is **child** |
| `related_required_skill_count` | Required skills whose best evidence is **related** |
| `missing_required_skill_count` | Required skills with no ontology evidence |
| `preferred_skill_count` / `matched_preferred_skill_count` | Preferred exact coverage |
| `required_skill_coverage` | `matched_required / required` (1.0 if none required) |
| `preferred_skill_coverage` | `matched_preferred / preferred` (1.0 if none preferred) |

Child/parent/related **do not** increment `matched_required_skill_count`. Docker never satisfies Kubernetes.

### Ontology features

`exact_alias_matches`, `parent_matches`, `child_matches`, `related_matches`, `average_gap_distance` (mean hops for non-exact, non-missing required evidence).

### Semantic features

`profile_job_cosine` when both embeddings are current and compatible. `semantic_similarity_available=false` and cosine `null` when missing, stale, or incompatible. Optional `relevant_project_cosine` / `relevant_experience_cosine` are max item-vs-job cosines when those vectors exist and are compatible.

Matching **does not encode**. It reuses stored Phase 6 vectors and `get_encoder()` only for identity.

### Experience / education / projects

| Feature | Policy |
|---|---|
| `candidate_experience_years` | Sum of `years_experience` only if **every** experience item has that field. Otherwise `null`. Dates are not converted into years. Empty experience is unknown, not zero. |
| `required_experience_years` | From confirmed job requirements, or `null` |
| `experience_satisfied` | `true` / `false` / `null` (unknown) |
| `education_requirement_present` | Job listed an education level |
| `education_alignment` | Case-insensitive equality of `education_level`. `null` if candidate education is unknown |
| `relevant_project_count` | Count of projects whose embedding cosine vs the job is ≥ the configured heuristic threshold |
| `project_evidence_present` | True only when relevant project evidence exists |

## Scoring weights (`baseline-weights-v1`)

Configurable via settings. Defaults:

| Component | Weight |
|---|---|
| Required skill coverage (exact only) | 0.60 |
| Preferred skill coverage (exact only) | 0.10 |
| Semantic similarity (`max(0, cosine)`) | 0.15 |
| Experience | 0.10 |
| Education + projects (equal split) | 0.05 |

These are **default starting weights only**. They are not empirically optimal.

```
current_match = sum(component_value * weight for available components) / sum(available weights)
```

Range: **0.0–1.0** only (four decimal places in the DTO). Not a percentage. Not accuracy.

Unavailable semantic similarity drops that weight and **renormalizes**. Ontology matching still runs. Required skills still dominate.

### Component policies

- **Required coverage:** exact canonical ID or alias→same ID. Child/parent/related credit for the required component is **0.0** (`RELATED_REQUIRED_CREDIT=0.0`). They appear in traces and gaps only.
- **Preferred:** missing preferred skills are not punished like missing required skills; coverage is matched/preferred (0 preferred → 1.0).
- **Experience:** no job minimum → component 1.0 (no penalty). Unknown candidate years with a minimum → component 1.0 (not a failure). Years below minimum → `candidate/required`.
- **Education:** no job requirement → no penalty. Unknown candidate education with a requirement → not a failure (alignment `null`, component does not penalize). Explicit mismatch → 0 for the education half of the 5% bucket.
- **Projects:** no projects → do not penalize. Projects present but none above the cosine heuristic → 0 for the project half. Threshold default **0.45**, documented as a baseline heuristic, not a validated cutoff.

## Exact / alias / hierarchy / related

Uses only curated ontology relationships (`OntologyService` / `classify_relationship`). Embeddings are not used to invent hierarchy.

| Job requires | Candidate has | Evidence | Required coverage |
|---|---|---|---|
| Machine Learning | ML (alias) | `alias_match` / exact | counts as matched |
| Machine Learning | Machine Learning | `exact_match` | counts as matched |
| Machine Learning | Deep Learning (child) | `hierarchy_child` | not matched; gap type `child` |
| Deep Learning | Machine Learning (parent) | `hierarchy_parent` | not matched; gap type `parent` |
| Kubernetes | Docker (`related_to`) | `related_skill` | not matched; gap type `related` |
| Kubernetes | Python | `missing_skill` | not matched; gap type `missing` |

Multiple mentions that resolve to one canonical skill collapse to one `CandidateSkill` on confirm and one evidence row here.

## Missing-data and embedding fallback

Do not fabricate skills, years, education, project relevance, or cosine.

| Situation | Behavior |
|---|---|
| No confirmed profile or job requirements | `409` |
| Missing / stale / incompatible embeddings | `semantic_similarity=null`, `semantic_similarity_available=false`, score from remaining components |
| Unknown experience/education | `null` in features; documented no-penalty unless an explicit mismatch exists |

## Persistence

Every scoring call that is not a counterfactual **inserts** a new `match_run` (no overwrite), a `feature_snapshots` row with the full feature JSON, and `match_explanations.traces`. `MatchRun.current_match` is `Numeric(5,2)` so the stored column is rounded to two decimals; the DTO uses four. Reconstruct the composer from the snapshot features + policy.

- `potential = null`
- `scoring_mode = baseline`
- `model_version = null`

## Match result DTO

Public fields include `current_match`, `potential=null`, `semantic_similarity`, `scoring_mode`, `model_version=null`, schema/ontology versions, matched/partial/related/missing skills, gaps, explanations, and component breakdown. Internal SQLAlchemy models are not returned.

## Explanation traces

Structured JSON only (no LLM): `alias_match`, `exact_match`, `hierarchy_child`, `hierarchy_parent`, `related_skill`, `missing_skill`, `preferred_skill`, `semantic_similarity`, `experience_match`, `experience_gap`, `experience_unknown`, `education_match`, `project_evidence`.

## Counterfactual

`simulate_add_skill` / `POST /api/v1/candidates/{id}/jobs/{job_id}/counterfactual` adds a hypothetical canonical skill **in memory**, recomputes features and baseline score, and returns delta. It does **not** write candidate skills or persist a match run. This is not career recommendation.

## APIs and authorization

| Method | Path | Who |
|---|---|---|
| GET | `/api/v1/candidates/{candidate_id}/jobs` | Owner or admin |
| GET | `/api/v1/candidates/{candidate_id}/jobs/{job_id}/match` | Owner, org recruiter in talent-pool scope, or admin |
| POST | `/api/v1/candidates/{candidate_id}/jobs/{job_id}/counterfactual` | Owner or admin |
| GET | `/api/v1/jobs/{job_id}/candidates` | Org recruiter or admin; **baseline** `current_match DESC` |

Candidate job visibility: confirmed requirements and status not `closed` / `archived` / `paused` (draft and open are included so the lab UI works without a publish flow). Recruiter candidate visibility: existing `can_recruiter_view_candidate` / `CANDIDATE_VISIBILITY_MODE`. IDs from the client are not trusted.

## Frontend

Functional pages only: `/candidate/jobs`, `/candidate/jobs/[jobId]`, `/recruiter/jobs/[jobId]/candidates`. Label: **Baseline Match**. Never “AI Score.”
