# Potential — heuristic gap closability

**Status: Phase 8 implemented.** Potential is a deterministic heuristic for remaining required skill gaps. It is **not** current match, not ranking, and not a trained model.

> Potential is a deterministic heuristic for gap closability. It is not a probability of hiring, selection, or future performance.

These weights and thresholds are **starting heuristics**. They are not empirically validated.

## Current match vs potential

| Signal | Question | Must not do |
|---|---|---|
| **Current match** | What does the candidate already satisfy? | Inflate because a related skill exists |
| **Potential** | How realistically can remaining **required** gaps close? | Equal current match, or default to 1.0 / 100 |

Example: job requires Machine Learning, Python, Kubernetes; candidate has Machine Learning, Python, Docker.

- Current: ML exact, Python exact, Kubernetes **missing as mastery** (related evidence only). Docker does **not** become Kubernetes.
- Potential: Kubernetes is relatively closable because Docker is `related_to` Kubernetes.

## When potential is not applicable

If there are **no required gaps** (every required skill is exact, or the job lists no required skills):

- `potential = null`
- `potential_status = "not_applicable"`

A complete current match is **not** assigned potential 1.0. Preferred-only gaps do not create a potential score. Required gaps dominate; preferred gaps contribute at most 15% of the graph component.

## Gap closability

A required skill is a potential gap when current evidence is not `exact` (`missing`, `child`, `parent`, or `related`). For each gap the composer stores:

- shortest ontology path from a candidate skill (bounded)
- relation type and distance
- `adjacent` if distance is 1 or the current-match kind is child/parent/related
- `graph_score` from relationship weights

This is **closability evidence**, not a claim that the candidate already knows the missing skill.

## Ontology path and distance

Traversal uses the cached ontology graph (`children`, `parents`, `related`, `similar`) with `seen` to avoid cycles. Default maximum depth: `POTENTIAL_MAX_GRAPH_DISTANCE=2`.

| Distance | Meaning |
|---|---|
| 0 | Same canonical skill (not used for potential gaps) |
| 1 | Direct ontology edge |
| 2 | Two-hop path; score multiplied by `two_hop_factor` (0.5) |
| > max | Not adjacent; graph score 0 |

Do not treat a path as exact mastery.

## Relationship weights (`potential-weights-v1`)

Independent of Phase 7 current-match weights.

| Relation | Weight |
|---|---|
| exact | 1.0 |
| child | 0.8 |
| parent | 0.5 |
| related | 0.6 |
| similar | 0.5 |
| two-hop | direct weight × 0.5 |

Child vs parent uses the **job-perspective** classifier (job requires ML, candidate has DL → child).

## Adjacent skill ratio

`adjacent_missing_skills / total_required_gaps`. Unrelated missing skills do not count. Returned as `potential_adjacent_skill_ratio`.

## Project / experience / certification / semantic

- **Projects:** confirmed project name/description overlap with the gap skill, aliases, or 1-hop neighbors (e.g. OpenCV adjacent to Computer Vision). Optional recency: unknown dates are **not** penalized; very old dates use factor 0.7. Missing projects → component `null` (unavailable), not 0.
- **Experience:** same overlap policy on title/employer/description. Related experience is not inferred mastery.
- **Certifications:** confirmed items only. Name overlap with gap vocabulary. A generic cert does not prove a missing skill.
- **Semantic:** supporting only. Cosine must be available and ≥ `POTENTIAL_SEMANTIC_COSINE_THRESHOLD` (default **0.45**, heuristic). Below threshold → 0 for that component if embeddings exist. Missing embeddings → component `null`.

Protected attributes, names, college prestige, and unrelated personal data are not inputs.

## Potential composer

Unavailable components are omitted and remaining weights **renormalize**. Missing data is not automatically zero.

| Component | Default weight |
|---|---|
| Graph closability | 40% |
| Adjacent skill ratio | 20% |
| Projects | 15% |
| Experience | 15% |
| Certifications | 5% |
| Semantic | 5% |

Range **0.0–1.0**. Deterministic for the same confirmed profile, job, ontology, embeddings, and policy.

Graph closability = `0.85 * mean(required gap scores) + 0.15 * mean(preferred gap scores)` so preferred matches cannot rescue an unrelated required set.

## Feature schema

Phase 7 `feature-schema-v1` field meanings are unchanged. Snapshots now use **`feature-schema-v2`**: v1 fields plus `potential_*` keys. The baseline composer still reads only v1 fields. `current_match` is composed **before** potential and is never overwritten by potential.

## Persistence and DTO

`match_runs` store `current_match`, `potential`, `semantic_similarity`, `scoring_mode=baseline`, `model_version=null`. Explanation traces include `potential_gap`, `potential_adjacent`, `potential_graph_path`, `potential_project`, `potential_experience`, `potential_certification`, `potential_semantic`.

`MatchResult` adds `potential`, `potential_status`, `potential_components`, and (candidate/admin only) `suggested_skill_paths`. Recruiter match detail does not include private career paths.

## Suggested skill path

Bounded shortest paths from owned skills toward required gaps. Labeled **Suggested Skill Path**, not a guaranteed career path. API: `GET /api/v1/candidates/{id}/career-paths` (`job_id` optional). Candidate owner or admin diagnostic only. **Recruiters receive 403.**

## Counterfactuals

`POST .../counterfactual` recomputes current match and potential **in memory**. It does not write `candidate_skills`, profiles, `feature_snapshots`, or `match_runs`.

## Privacy

Potential evidence on recruiter views is limited to match scores, coverage, missing/related required skills. Private growth planning stays on candidate (and admin) career-path endpoints.

## Limitations

- Heuristic weights, not trained or calibrated
- Seed ontology is small; missing edges look like unclosable gaps
- Hashing embeddings in tests are not semantic meaning
- Recency is optional and unused when dates are absent
- No XGBoost, no hiring labels, no selection probability
