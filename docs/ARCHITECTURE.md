# PRJ_385 — Technical Architecture

**Project:** AI-Based Recruitment Recommendation Engine  
**Domain:** Machine Learning + Analytics  
**SDG:** SDG 9 — Industry, Innovation and Infrastructure  
**Status:** Phase 10 offline XGBoost training, model registry, and safe inference are implemented on top of Phase 9 dataset snapshots. Training refuses insufficient real labels. Recruiter shortlist/reject decisions are behavioral labels and are not ground-truth hiring outcomes. No trained project model is produced until sufficient real labeled data exists. Potential is gap closability, not a hiring probability. Embeddings provide semantic similarity features. They do not produce the final recruitment score.

**Innovation:** Semantic and hierarchical skill understanding with potential-aware and explainable recruitment recommendations.

## Phase 0 runtime

```
Next.js
  ↓  HTTP /api/v1
FastAPI modular monolith
  ↓
PostgreSQL 16 + pgvector
  ↓  (later phases, not running yet)
NLP / Ontology / Embeddings / Matching / ML / Ranking / Explainability
```

| Layer | Responsibility |
|---|---|
| NLP | Extracts information from resumes and job descriptions |
| Ontology | Normalizes skills; aliases, hierarchy, relatedness |
| Embeddings | Semantic similarity (frozen encoder, cosine) |
| Matching | Deterministic comparison using ontology policy |
| ML | Learns from engineered features when labels exist |
| Ranking | Orders candidates or jobs |
| Explainability | Structured traces, not generated prose |

### Dependency rules (enforced by package layout)

- API routers call module services. Routers stay thin.
- Services contain application logic. Repositories contain database access. Schemas are DTOs.
- NLP must not import ML.
- ML must not import FastAPI (`app/modules/ml` has no `router.py`).
- Matching must not import ranking or ML.
- Frontend must not access PostgreSQL, contain ML logic, or contain ranking weights.
- Training code (`ml/`) must not depend on HTTP requests.
- Replacing `RANKER_IMPL` must not change the frontend API contract.

## Phase 1 database layer (implemented)

SQLAlchemy 2 models live in `backend/app/models/` and are **not** API DTOs. Alembic `0002_core_domain_schema` creates the tables. pgvector is enabled by `0001_enable_pgvector`.

Models are grouped as: identity, candidates, ontology, jobs, applications, intelligence, ml, ops.

### Cascade and deletion policy

| Delete | Cascades | Preserved |
|---|---|---|
| Resume | `extraction_revisions`; embeddings must be deleted by the application (`owner_type` + `owner_id`, no FK) | Confirmed `candidate_profiles` (`source_revision_id` SET NULL). Candidate account is not deleted. |
| Candidate profile | experience, education, projects, certifications, `candidate_skills` | Candidate, other profiles |
| Candidate account | resumes, profiles, applications, candidate/recruiter decisions involving that candidate, match_runs | Organization, jobs |
| Organization | members, jobs (and job requirements/skills) | Users |
| Skill | aliases, relations | Blocked if referenced by candidate_skills or job skills (RESTRICT) |
| Match run | explanations, feature_snapshots | — |

Refresh tokens: only `token_hash` is stored. Passwords: only `password_hash`.

### Embeddings index

`embeddings.vector` uses pgvector `VECTOR` **without a fixed dimension**. No HNSW/IVFFlat index yet — the encoder (and therefore dimension) is not selected. Changing the encoder is a full re-embed keyed by `model_name` + `model_version`.

### Ontology matching policy (not in the database)

`parent_of` / `related_to` are graph edges only. The database does **not** treat parent possession as mastery of children. That rule is implemented later in `matching/`.

Idempotent seed: `python scripts/seed_ontology.py` (draft version `seed-0.1`, no users or scores).

This document is the implementation contract for the project team. It separates four concerns that must not be collapsed into a single “AI” black box:

1. **Deterministic NLP processing** — parse documents, extract fields, normalize skills.
2. **Semantic similarity** — embedding cosine similarity; not a trained ranker.
3. **ML prediction** — a real trainable model (initially XGBoost) over engineered features.
4. **Recommendation / ranking** — assemble scores, order candidates or jobs, attach explanations.

An LLM is **not** the recommendation model. If used later, it may only verbalize structured explanation traces already produced by the scoring stack.

---

## Design constraints (non-negotiable)

| Constraint | Decision |
|---|---|
| Topology | Modular monolith (one FastAPI process, internal modules). No microservices unless a later bottleneck is measured. |
| Frontend isolation | UI talks only to versioned HTTP APIs. Models can be swapped without frontend changes. |
| Scoring honesty | No fake ML outputs. Until a model is trained and evaluated, the API must label scores as `baseline` or `untrained`. |
| Data honesty | No dataset is assumed to exist. Training cannot start until labels, target variable, and evaluation protocol are decided. |
| Replaceability | Every scoring component implements a stable Python protocol. Baseline and trained implementations share the same interface. |
| Scope of ontology | Start with a curated CS/IT skill graph. Do not claim a universal labor-market ontology. |

---

## 1. Overall system architecture

### 1.1 Shape

Two deployable applications plus one database:

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js (React / TypeScript / Tailwind / shadcn)               │
│  Candidate app · Recruiter app · Admin app                      │
│  No ML imports. No direct DB. No embedding calls.               │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS JSON (OpenAPI)
┌────────────────────────────▼────────────────────────────────────┐
│  FastAPI modular monolith                                       │
│  Identity · Documents · NLP · Ontology · Embeddings             │
│  Matching · Features · ML Inference · Ranking                   │
│  Explainability · Career Path · Analytics · Admin               │
│  Optional in-process worker (same image) for async jobs         │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
                ▼                             ▼
     PostgreSQL + pgvector          Object storage (local disk
     (OLTP + vectors +              in dev; S3-compatible later)
      model metadata)
```

A third process (Redis + worker) is **optional Phase 6+** if PDF parsing and embedding become too slow for request/response. Until then, FastAPI `BackgroundTasks` or a simple in-process queue is enough.

### 1.2 Runtime layers

| Layer | Responsibility | Must not do |
|---|---|---|
| Presentation | Auth’d UI, charts, explanation rendering | Compute match scores |
| API / application | AuthZ, orchestration, DTOs, job enqueue | Own ML weights |
| Domain modules | Ontology, matching rules, feature contracts | Talk to React |
| Intelligence | Embeddings, XGBoost, SHAP | Persist PII except through domain APIs |
| Data | PostgreSQL, files, model artifacts | Business ranking logic |

### 1.3 Why not microservices

A 7th-semester team cannot operate NLP, embedding, ranking, and analytics as separate services without paying a large ops tax. Module boundaries inside one FastAPI app give the same mental model (replace `ml/` without touching `nlp/`) without network failure modes. Split later only if embedding latency or training jobs block the API.

---

## 2. Frontend architecture

### 2.1 Application structure

Next.js App Router, TypeScript, Tailwind, shadcn/ui.

```
frontend/
  app/
    (public)/          login, register, landing
    (candidate)/       resume, profile, matches, gaps, career path
    (recruiter)/       jobs, candidates, compare, shortlist, analytics
    (admin)/           users, ontology editor, model registry, audits
  components/          ui primitives + domain widgets
  lib/
    api.ts             typed client generated from OpenAPI
    auth.ts
    types.ts           DTOs only — mirrors backend schemas
  hooks/
```

Route groups enforce **role layouts**. Middleware checks the session cookie and redirects by role. Recruiters never mount candidate-only pages and vice versa.

### 2.2 Data access rule

The frontend consumes **result DTOs**, not model internals:

```ts
type ScoringMode = "baseline" | "trained";

type MatchResult = {
  current_match: number;          // 0–100
  potential: number;              // 0–100
  semantic_similarity: number;    // 0–1
  project_relevance: number;
  experience_relevance: number;
  scoring_mode: ScoringMode;
  model_version: string | null;
  explanations: ExplanationTrace[];
  skill_gaps: SkillGap[];
};
```

`scoring_mode` and `model_version` are mandatory so the UI can badge “Baseline (rules)” vs “Model v3” and never imply a trained model when none exists.

### 2.3 UI composition (by user)

**Candidate:** upload resume → processing status → editable extracted profile → job list ranked for them → match detail (current, potential, gaps, explanation, career path).

**Recruiter:** create job → processing status → ranked candidates → compare (side-by-side traces) → shortlist / reject (this is **label collection**) → analytics.

**Admin:** users/orgs, ontology CRUD, embedding reindex, model registry (which artifact is `active`), audit log.

### 2.4 State

- Server Components for first paint of lists.
- Client Components for score breakdowns, comparison, charts.
- TanStack Query (or SWR) for API cache. No global ML state.

### 2.5 What the frontend must never contain

Skill synonym tables, embedding calls, XGBoost, ranking weights, SHAP math. If a weight changes, only the API response changes.

---

## 3. Backend architecture

### 3.1 Modular monolith

One FastAPI app, one Docker image, modules imported as packages. Each module owns: router (optional), service, repository, schemas, tests.

```
backend/app/
  main.py                 composition root
  core/                   config, logging, security, db session
  api/v1/                 HTTP routers only (thin)
  modules/
    identity/
    organizations/
    documents/
    nlp/
    ontology/
    embeddings/
    matching/
    features/
    ml/
    ranking/
    explainability/
    career/
    analytics/
    jobs/
    candidates/
    applications/
```

`api/v1` depends on module services. Modules must not import routers. `ml` must not import FastAPI. `nlp` must not import `ml`.

### 3.2 Dependency direction

```
api  →  ranking  →  ml
                 →  matching  →  ontology
                              →  embeddings
                 →  features  →  matching, ontology, embeddings
        explainability → ranking, ml, matching
        nlp → ontology
        documents → nlp
        analytics → applications, ranking (read models)
```

Forbidden: `nlp → ml`, `frontend concepts in backend`, `matching → ranking` (ranking may call matching, not the reverse).

### 3.3 Sync vs async

| Operation | Mode | Reason |
|---|---|---|
| Login, CRUD, fetch scores already computed | Sync HTTP | Low latency |
| PDF/DOCX parse, skill extract, embed, full match | Async job | Seconds, CPU-heavy |
| Model training | Offline CLI / scheduled job | Minutes–hours, not in request path |
| Inference (XGBoost) | Sync inside ranking, after features exist | Milliseconds |

Job table: `processing_jobs(id, type, status, payload, error, started_at, finished_at)`.

Phase 3 `resume_parse` jobs are created and executed in-process by `ResumeParseProcessor` so a worker can replace the run step later. Redis/Celery are not used.

### 3.4 Composition root (model swap)

```python
# core/container.py (conceptual)
ranker: RankerProtocol = load_ranker(settings.RANKER_IMPL)
# RANKER_IMPL = "baseline" | "xgboost"
```

Config selects the implementation. No code change in routers or frontend.

---

## 4. Database architecture

PostgreSQL 16 + `pgvector`. No Neo4j in v1: the skill graph is stored as relational edges and loaded into a bounded in-memory graph (`app/modules/ontology/graph.py`) for traversal.

### 4.1 Core entities (logical)

**Identity & tenancy**

- `users` — id, email, password_hash, role (`candidate|recruiter|admin`), status
- `organizations` — recruiter tenancy
- `organization_members` — user ↔ org
- `sessions` / refresh tokens

**Candidate**

- `candidates` — user_id, headline, location, preferences (JSONB: roles, locations, job types)
- `resumes` — candidate_id, storage_key, mime, sha256, parse_status, parsed_at
- `candidate_profiles` — canonical extracted + user-edited profile (skills, education, experience, projects, certs). **Edited profile is source of truth after confirmation.**
- `experience_items`, `education_items`, `project_items`, `certification_items`

**Jobs**

- `jobs` — org_id, title, description_raw, status, location, seniority, preference filters
- `job_requirements` — structured: required_skills[], preferred_skills[], min_years, education_gate, certs

**Ontology**

- `skills` — id, canonical_name, slug, description, category, status
- `skill_aliases` — skill_id, alias, source (`curated|extracted|import`), unique(alias normalized)
- `skill_relations` — parent_id, child_id, relation (`parent_of|related_to|similar_to`), weight
- `ontology_versions` — version, checksum, activated_at (reproducible matching)

**Intelligence**

- `embeddings` — owner_type (`resume_chunk|profile|job|skill`), owner_id, model_name, dim, vector, content_hash
- `match_runs` — candidate_id, job_id, scoring_mode, model_version, current_match, potential, feature_snapshot JSONB, created_at
- `match_explanations` — match_run_id, traces JSONB
- `ml_models` — version, artifact_uri, feature_schema_version, metrics JSONB, status (`candidate|active|rejected|retired`)
- `ml_training_runs` — dataset_snapshot_id, params, metrics, git_sha
- `feature_snapshots` — frozen feature vectors used for a prediction (audit + training)

**Feedback (labels for future training)**

- `recruiter_decisions` — append-only `recruiter_id`, `organization_id`, `candidate_id`, `job_id`, `action` (`shortlist|reject|review` plus legacy view/compare/hire), optional `reason`/`note`, `match_run_id`, `feature_snapshot_id`, `created_at`. Behavioral labels, not hiring outcomes. See `docs/DATASET.md`.
- `candidate_decisions` — save/apply/dismiss
- `dataset_snapshots` — immutable point-in-time training rows. Phase 10 trains from them only when eligible.

**Analytics**

- Prefer querying `match_runs` + `recruiter_decisions`. Add `analytics_events` only for UI funnel events that are not already implicit in tables.

### 4.2 Indexes

- Unique normalized alias on `skill_aliases`
- `(candidate_id, job_id, created_at desc)` on `match_runs`
- HNSW or IVFFlat on `embeddings.vector` (choose after measuring; HNSW is the default starting point for <1M vectors)
- Org-scoped indexes on `jobs`, `recruiter_decisions`

### 4.3 Profile dual-write rule

Parser output lands in `extraction_revisions`. The candidate confirms/edits into `candidate_profiles`. Matching **always** uses the confirmed profile, not raw parse, except for the first automatic run before confirmation (flagged `unconfirmed_profile=true`).

---

## 5. ML architecture

### 5.1 Role of ML in this system

ML does **not** extract skills (NLP + ontology do).  
ML does **not** compute cosine similarity (embeddings do).  
ML **does** learn a mapping from a **feature vector** (built from NLP, ontology, and embeddings) to a **target variable** that the team must still define.

Primary trainable component: **gradient-boosted trees (XGBoost)** for tabular features. Optional later: a learned ranker (LambdaMART / XGBoost ranker) if pairwise labels exist.

Sentence-Transformers are **frozen encoders** in v1, not fine-tuned, unless a later phase has enough in-domain pairs and an evaluation set. Fine-tuning is a separate decision, not the default.

### 5.2 Protocols (stable)

```python
class FeatureExtractor(Protocol):
    schema_version: str
    def transform(self, candidate: Profile, job: Job, ctx: MatchContext) -> FeatureVector: ...

class PotentialScorer(Protocol):
    def score(self, features: FeatureVector) -> Score: ...

class MatchPredictor(Protocol):
    def predict(self, features: FeatureVector) -> Prediction: ...  # P(target) or relevance

class Ranker(Protocol):
    def rank(self, items: list[ScoredItem], features: list[FeatureVector]) -> list[RankedItem]: ...
```

Baseline classes implement the same protocols as XGBoost classes.

### 5.3 Feature vector (v1 contract)

Features are deterministic functions of profile + job + ontology + embeddings. Names are versioned (`feature_schema_v1`).

**Skill / ontology**

- `req_skill_exact_coverage`
- `req_skill_alias_coverage`
- `req_skill_hierarchy_coverage` (child/parent hits)
- `req_skill_related_coverage`
- `preferred_skill_coverage`
- `unmatched_required_count`
- `mean_gap_ontology_distance` (missing required skill → nearest candidate skill)
- `min_gap_ontology_distance`
- `hierarchy_depth_bonus`

**Semantic**

- `profile_job_cosine`
- `skills_text_job_cosine`
- `max_project_job_cosine`
- `mean_experience_job_cosine`

**Experience / education / projects / certs**

- `years_experience`
- `years_gap_vs_required` (signed)
- `title_similarity_max`
- `education_level_match`
- `field_of_study_cosine`
- `cert_required_hit_rate`
- `project_count_relevant` (cosine above threshold)
- `recency_weighted_project_score`

**Potential-specific**

- `adjacent_skill_ratio` (candidate skills that are 1-hop from a missing required skill)
- `learnability_index` (inverse mean gap distance, capped)
- `recent_adjacent_learning` (projects/certs in last N months near gaps)
- `preference_alignment` (location, role family, job type)

**Meta**

- `profile_completeness`
- `ontology_version_id` (not a model feature; stored for audit)

No protected attributes (gender, race, age, photo) in features. Names and photos must not be embedded into the feature vector.

### 5.4 Baseline vs trained

| Component | Phase 1–4 | After labels exist |
|---|---|---|
| Feature extractor | Rules + math | Same extractor (do not change casually) |
| Current match | Weighted sum of coverage + semantic + experience + projects | Optional: model head **or** keep interpretable weighted sum |
| Potential | Ontology-distance + recency heuristics | XGBoost / second head using potential features + outcomes |
| Final rank | Sort by `α·current + β·potential` | XGBoost ranker or learned `α,β` under evaluation |

**Recommendation:** keep **current match** as an interpretable formula even after ML exists. Use ML for (a) potential / outcome probability and/or (b) a final relevance score that is **shown separately** from current match. Mixing them into one opaque number destroys the product differentiator.

### 5.5 Model artifact layout

```
ml/artifacts/
  {model_version}/
    model.json          # XGBoost
    feature_schema.json
    metrics.json
    training_config.yaml
    shap_baseline.json  # optional
```

`ml_models.active` points to one version. Inference loads that artifact at process start or via a safe hot-reload.

---

## 6. NLP pipeline

Implemented in Phase 4. **NLP extraction is not semantic skill normalization.**

```
document text → section detection → preprocessing
  → spaCy blank + PhraseMatcher / lexicon spans
  → ProfileDraft or JobRequirementsDraft
  → candidate/recruiter review
  → confirm → candidate_profiles / job_requirements
```

- Pipeline version: `nlp-v1` (`NLP_PIPELINE_VERSION`).
- Skills are **raw mentions**. `ML` and `Machine Learning` stay distinct.
- Evidence spans are stored for later explainability. Extraction confidence is not a match score.
- Confirmed profiles are not overwritten by re-parse.
- Canonical `candidate_skills.skill_id` is **not** populated yet (no ontology).
- English only. No transformer NER. No LLM rewrite of summaries.

### 6.1 Document I/O

- PDF: `pypdf` / `pdfminer.six`; fallback note when text is empty (scanned PDF).
- DOCX: `python-docx`.
- Reject `.doc` binary unless a later library is added.
- OCR (**optional Phase 5+**): Tesseract only if scanned resumes are in scope. Default: mark `parse_status=needs_ocr` and ask the candidate to paste text or upload a digital PDF.

### 6.2 Section segmentation

Rule-based heading detection first (Education, Experience, Projects, Skills, Certifications, Summary). spaCy `Sentencizer` + custom matcher for headings. Transformer NER is **optional** and must beat the rule baseline on a labeled extraction set before replacing it.

### 6.3 Extraction

| Field | v1 method | Later |
|---|---|---|
| Email, phone, URLs | Regex | Same |
| Education org, degree, dates | spaCy + patterns | Fine-tuned NER if labeled |
| Job titles, employers, dates | Patterns + dateparser | Same |
| Project name + bullets | Section parse | Same |
| Skill spans | Conservative lexicon + spaCy PhraseMatcher (raw mentions) | Ontology aliases |
| Years of experience | Date math + explicit “X years” patterns | Same |

### 6.4 Quality gates

Every extraction stores `confidence` and `evidence_span` (char offsets). Low-confidence fields surface in the candidate review UI. Matching should down-weight unconfirmed low-confidence skills.

### 6.5 Languages

v1: English resumes and JDs only. State this as a project scope limit.

---

## 7. Skill normalization architecture

Implemented in Phase 5. **Skill normalization is not candidate-job matching.**

Normalization is a **pure function**: `raw_span + ontology_version → SkillNormalizationResult`.

Steps:

1. Unicode NFKC lookup key that preserves `C++`, `C#`, `.NET`, `Node.js`, `CI/CD`, `scikit-learn`.
2. Exact canonical name.
3. Exact alias, then normalized alias.
4. Optional RapidFuzz only if score ≥ threshold **and** the winner is unique; otherwise `unmatched` / needs review.
5. Record `resolution_type`: `canonical | alias | fuzzy | unmatched`.
6. Never invent a canonical skill. Unmatched mentions stay on the draft for human review.

**Idempotency:** same span + same ontology version → same skill id.

**Candidate edits:** re-parse writes a new draft. Confirmed `candidate_skills` are not overwritten.

---

## 8. Skill ontology / knowledge graph approach

### 8.1 Model

Directed graph with typed edges:

- `parent_of` — hierarchy (AI → Machine Learning → Deep Learning)
- `related_to` — lateral (NLP related_to Machine Learning)
- `similar_to` — near-synonym concepts that are still distinct canonical nodes (if needed)

Aliases are **not** nodes. They hang off canonical skills.

### 8.2 Storage vs compute

- Source of truth: PostgreSQL tables + `ontology_versions`.
- Runtime graph: bounded in-memory adjacency lists from the active `graph_snapshot` (not unrestricted recursion).
- Traversal: parent closure (does candidate skill satisfy a more general requirement?), child closure (does a general resume skill weakly support a specific requirement? — **usually no**; specificity rules below).

### 8.3 Matching policy (must be explicit)

| Job requires | Candidate has | Result |
|---|---|---|
| Machine Learning | ML (alias) | Full skill match |
| Machine Learning | Deep Learning (child) | Partial hierarchical match (weight < 1) |
| Deep Learning | Machine Learning (parent) | Weak / potential signal, **not** full current match |
| Machine Learning | NLP (`related_to`) | Related credit toward **potential**, small current credit |
| Kubernetes | Docker (related, 1 hop) | Potential / gap-closability, not current match |

This policy is encoded in `app/modules/ontology/policies.py` and consumed by `app/modules/matching/`. Child/parent/related evidence is never treated as an exact required-skill match. See `docs/MATCHING.md`.

### 8.4 Seed ontology

v1 is **team-curated** for CS/IT recruitment (the project domain). Size target: hundreds of skills, not millions.

**Allowed later imports (team decision, license check required):** ESCO, O*NET, public skill lists. None of these are assumed present. Import must produce a new `ontology_version` and a diff review.

### 8.5 Governance

Admin UI: add skill, alias, edge, deprecate node. Publishing creates a new version. In-flight match jobs pin `ontology_version_id`.

---

## 9. Embedding pipeline

**Implemented in Phase 6.** Embeddings provide semantic similarity features. They do not produce the final recruitment score.

### 9.1 Encoder

Local Sentence-Transformers **MiniLM** model, configurable:

- `EMBEDDING_MODEL_NAME` default `sentence-transformers/all-MiniLM-L6-v2`
- `EMBEDDING_MODEL_VERSION` default `all-minilm-l6-v2-v1` (application pin; **not** a Hugging Face git SHA)
- `EMBEDDING_MODEL_REVISION` optional Hugging Face snapshot. Empty uses the library default and does **not** claim a SHA.
- Dimension is read from the loaded encoder at runtime. Stored length must equal encoder dimension. Vectors are never padded or truncated.
- `EMBEDDING_BACKEND=sentence_transformers` in production. `hashing` is a test stand-in with identity `hashing-encoder` / `hashing-v1` (8-d). Hashing vectors are never stored as MiniLM.
- Docker installs CPU PyTorch, then `sentence-transformers`. Do not use the hashing backend in Compose.

### 9.2 Text version

The text builder version `embedding-text-v1` is authoritative. `EMBEDDING_TEXT_VERSION` must match it or the API refuses to embed. Changing the builder requires bumping the constant and the setting together.

Deterministic builders:

| Object | Text |
|---|---|
| Confirmed profile | summary, canonical skills, experience, projects, education, certifications |
| Experience | title, employer, description, technologies |
| Project | name, description, technologies |
| Confirmed job | title, description, required/preferred **canonical** skills, education, years |
| Job requirements | canonical confirmed skills; unmatched raw mentions kept as evidence only, never as a canonical fallback |
| Resume chunks | existing extraction `sections` / `normalized_text`, split at 1800 characters, no overlap |

Matching-facing embeddings use **confirmed** data only. Chunks reuse Phase 3/4 extraction; PDFs are not parsed again.

### 9.3 Hashing and reuse

SHA-256 of normalized source text. Reuse when owner + hash + model + model version + text version match.

### 9.4 Similarity

Python cosine similarity on loaded vectors. pgvector `cosine_distance` (`<=>`) for top-K retrieval among compatible rows. Output is a number in `[-1, 1]`, not a percentage, not a rank.

Comparison requires the same model name, model version, dimensions, and embedding text version.

### 9.5 Status

`missing` | `current` | `stale` | `incompatible`. GET never re-embeds. POST embeds explicitly (in-process `processing_jobs`).

---

## 10. Recommendation engine architecture

The engine is an **orchestrator**, not a single model.

```
Profile + Job
    → MatchingService (ontology + rules + baseline composer)  # deterministic
    → Embedding features (stored cosine only; no encode-on-match)
    → FeatureExtractor (feature-schema-v1)
    → CurrentMatchComposer                         # interpretable 0.0–1.0
    → PotentialScorer (not implemented; always null)
    → Ranker                                       # not implemented
    → Explainer                                    # structured traces
    → Persist match_run
```

### 10.1 Two ranking directions

| Direction | Input | Output |
|---|---|---|
| Job → candidates | One job, N candidates in scope | Ranked candidates |
| Candidate → jobs | One candidate, N open jobs | Ranked jobs |

Same features, same scorers, different retrieval set and AuthZ filter.

### 10.2 Current match composer (interpretable)

```
current = 100 * clip(
  w1 * required_coverage_hybrid
+ w2 * semantic_similarity
+ w3 * experience_relevance
+ w4 * project_relevance
+ w5 * education_cert_score
)
```

`required_coverage_hybrid` uses the ontology policy in §8.3. Weights `w*` live in config (`ranking_weights_v1.yaml`), not in the frontend. Admin can edit weights; each match_run stores the weight set id.

### 10.3 Combining current and potential for sort order

Default recruiter sort: `current_match` descending. Alternate sorts: `potential`, `balanced = α·current + β·potential` with `α,β` shown in the UI. Do not hide the two scores behind one number on the detail page.

### 10.4 Hard filters vs soft scores

Apply **before** ranking:

- Work authorization / location if the team collects them as explicit filters
- Job status = open
- Org tenancy
- Optional: min education as a recruiter toggle (filter vs penalty)

---

## 11. Candidate potential scoring architecture

**Definition:** Potential estimates how well the candidate can **grow into unmatched requirements**, not how impressive they are in general.

### 11.1 Baseline potential (no labels required)

For each required skill `s` not fully matched:

- `d(s)` = shortest-path distance in the undirected `related_to`∪hierarchy graph from `s` to the candidate’s skill set (`inf` if disconnected)
- `closability(s)` = `1 / (1 + d(s))` or 0 if `inf`
- `gap_closability` = mean `closability`
- `adjacent_ratio` = fraction of gaps with `d(s) = 1`
- `learning_signal` = recency-weighted projects/certs whose embeddings or skills sit on the path toward gaps
- `education_alignment` = field-of-study cosine / ontology overlap with the job family

```
potential_baseline = 100 * clip(
  u1 * gap_closability
+ u2 * adjacent_ratio
+ u3 * learning_signal
+ u4 * education_alignment
+ u5 * preference_alignment
)
```

A **full required match** (no required gaps) yields `potential=null` / `potential_status=not_applicable` in the implemented Phase 8 policy. It does **not** assign 100. See `docs/POTENTIAL.md`.

### 11.2 Trained potential (only after labels)

Possible targets (team must pick one — see §D):

- P(shortlist | features) for **gapped** candidates
- P(hire)
- Expert “growth potential” Likert scores (small gold set)

XGBoost trains on the **same feature schema**, with emphasis on potential features. Output is calibrated (Platt / isotonic) on a validation set if probabilities are shown.

### 11.3 What potential must not do

- Reward keyword stuffing
- Use name, photo, or protected attributes
- Treat parent-skill possession as mastery of all children
- Be presented as a guarantee of future performance

---

## 12. Explainability architecture

Explanations are **data**, not chat.

### 12.1 Trace schema

```json
{
  "type": "alias_match",
  "job_skill": "ML",
  "canonical": "Machine Learning",
  "candidate_evidence": "Skills: Machine Learning",
  "weight": 1.0
}
```

Other types: `hierarchy_child`, `related_skill`, `semantic_chunk`, `experience_overlap`, `project_overlap`, `education`, `certification`, `gap`, `potential_adjacent`, `weight_contribution`, `shap_feature`.

### 12.2 Rendering

Frontend maps `type` to components (green match, amber partial, red gap). No model-generated prose in v1.

**Optional later:** an LLM receives **only** the JSON traces and produces a paragraph. If the LLM contradicts traces, the UI still shows traces as source of truth. This is NLG, not ranking.

### 12.3 SHAP

When XGBoost is active, compute SHAP on the inference feature vector. Map feature names through `feature_schema.json` to human labels. Cap displayed features (top 8). Store SHAP in `match_explanations`.

### 12.4 Counterfactuals (lightweight)

“If the candidate added skill X (1-hop from gap Y), estimated current match would rise by Z” — computed by **re-running the deterministic composer** with a hypothetical skill, not by asking an LLM. Useful for career path and candidate feedback.

---

## 13. Analytics architecture

Analytics reads operational tables; it does not re-implement matching.

**Recruiter / org**

- Score distributions (current vs potential) per job
- Skill demand (required skills frequency) vs internal supply (candidate skills)
- Gap heatmap: most common unmatched required skills
- Funnel: viewed → compared → shortlisted → (hired if recorded)
- Time-to-shortlist
- Overlap of top-k rankers (baseline vs trained) — **only when both exist**

**Admin / research**

- Extraction quality (if gold labels exist)
- Ontology coverage (% spans normalized)
- Model metrics over time (from `ml_training_runs`)
- Decision vs score calibration plots

**Candidate**

- Personal skill gap vs selected job families
- No org-wide analytics

**Implementation:** SQL views + FastAPI analytics endpoints + charts in the recruiter/admin UI (e.g. Recharts). Batch materialization only if queries become slow.

Do not invent dashboards that require hire outcomes the team does not collect.

---

## 14. Authentication and authorization architecture

Implemented in Phase 2. Details: `docs/SECURITY.md` and `docs/API.md`.

### 14.1 AuthN

- Email + password hashed with Argon2id.
- JWT access token (short, in-memory on the client) + refresh token (httpOnly cookie, SHA-256 hash in `refresh_sessions`).
- Refresh rotation, family reuse revocation, logout, logout-all.
- Optional later: OAuth (Google) — not required for v1.

### 14.2 AuthZ (RBAC + tenancy)

| Role | Can |
|---|---|
| Candidate | Own profile, own resumes, own match results against **open** jobs they are allowed to see, apply/save |
| Recruiter | Own org jobs, candidates **in scope** (applicants + sourced), decisions, org analytics |
| Admin | Users, ontology publish, model activation, audit logs, all-org break-glass |

Enforcement is FastAPI dependencies (`require_role`, `require_candidate_owner`, `require_org_member`). Next.js middleware is UX only.

**Scope rule:** recruiters do not see all candidates on the platform unless the product decision is a shared talent pool. Default policy: **applicants to their org’s jobs** + candidates who opted into discovery (`preferences.discoverable`). Configurable via `CANDIDATE_VISIBILITY_MODE`. **This is a product decision** (Question F).

### 14.3 API enforcement

Every router: current user loaded from PostgreSQL → role check → resource org/ownership check. IDs in URLs are untrusted. JWT `role` is not sufficient for sensitive mutations.

### 14.4 Audit

Log: registration, login success/failure, refresh, logout, logout-all, authorization denial, later ontology publish, model activate, recruiter export. No passwords, tokens, or raw resume text in logs.

### 14.5 CSRF, CORS, rate limits

Cookie-authenticated POSTs (`/auth/refresh`, `/auth/logout`) require a trusted `Origin` and/or `X-CSRF-Token`. CORS origins come from `CORS_ORIGINS` (never `*` with credentials). Login/register/refresh are rate-limited in-process; Redis is not used yet.

---

## 15. File upload / document processing architecture

Implemented in Phase 3. Details: `docs/API.md` and `docs/SECURITY.md`.

```
Client multipart upload
  → auth + ownership check
  → size / declared MIME / magic-byte check (PDF/DOCX only)
  → SHA-256 content-addressed blob under BLOB_ROOT/resumes/<sha256>
  → resumes row (parse_status=queued) + processing_jobs row
  → in-process document parser (document-parser-v1)
  → extraction_revisions (normalized text, optional rule-based sections)
  → parse_status=ready | failed | needs_ocr
```

Limits: `MAX_RESUME_BYTES` (default 5 MB). Virus scanning is **out of scope** (documented residual risk). OCR is **not implemented**; scanned/textless PDFs become `needs_ocr`.

Duplicate decision: same candidate + same SHA-256 returns the existing resume row (authorization stays per row). Different candidates may share the physical blob and `storage_key` while keeping separate `resumes` rows. Deleting a resume removes the blob only when no other resume still references that hash. Confirmed `candidate_profiles` are not deleted.

Storage is `LocalBlobStore`. The interface is replaceable with S3 later. Parser version is `document_parser_version` / `document-parser-v1`.

---

## 16. API architecture

REST, OpenAPI 3, version prefix `/api/v1`. JSON in/out. Idempotent PUT/PATCH where it matters.

### 16.1 Resource groups

| Group | Examples |
|---|---|
| Auth | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` |
| Me | `GET/PATCH /me`, `GET /me/matches` |
| Resumes | `POST /candidates/{id}/resumes`, list/detail/delete (Phase 3, metadata only) |
| Profile | `GET/PATCH /profile`, `POST /profile/confirm` |
| Jobs | CRUD `/jobs`, `POST /jobs/{id}/parse` |
| Matches | `GET /jobs/{id}/candidates`, `GET /candidates/{id}/jobs`, `GET /matches/{id}` |
| Shortlist | `POST /jobs/{id}/decisions` |
| Ontology | Admin CRUD `/admin/skills`, `/admin/ontology/publish` |
| Models | `GET /admin/models`, `POST /admin/models/{id}/activate` |
| Analytics | `/analytics/jobs/{id}/summary`, `/analytics/org/skills` |
| Career | `GET /matches/{id}/career-path` |

### 16.2 Match listing contract

Query: `sort=current|potential|balanced`, `min_current`, `skill_id`.  
Response includes `scoring_mode`, `model_version`, `ontology_version`.  
**Never** return raw feature vectors to recruiters in v1 (admin debug flag only).

### 16.3 Errors

RFC 7807 problem+json. Parse failures: 422 with machine-readable codes (`EMPTY_PDF_TEXT`, `UNSUPPORTED_MIME`).

### 16.4 Compatibility

Additive fields are OK. Renames require `/api/v2`. ML swap must not break v1 DTOs.

---

## 17. Data flow — resume to recommendation

1. Candidate authenticates.
2. Upload resume → blob + `resumes` row.
3. Worker extracts text; if empty, fail with `EMPTY_PDF_TEXT`.
4. NLP builds `ProfileDraft` (sections, spans, dates).
5. Skill spans normalized against **pinned** ontology version.
6. Candidate reviews/edits/confirms → `candidate_profiles`.
7. Embedding job writes profile (+ item) vectors.
8. System retrieves open jobs in scope (preferences as soft or hard filters — product decision).
9. For each job (or batched): matching + features + current composer + potential + explanations.
10. Persist `match_runs`. Return ranked jobs + scores + traces.
11. Career path endpoint: shortest ontology paths from possessed skills to gap skills for a selected job.

Batch cap: if jobs ≫ hundreds, prefilter by ANN embedding retrieval then full score top M. College scale: score all open jobs.

---

## 18. Data flow — job description to candidate ranking

1. Recruiter creates job (title, JD text, structured filters).
2. NLP extracts requirement draft: required/preferred skills, years, education, certs.
3. Recruiter **confirms** requirements (same dual-write pattern as profiles). Unconfirmed jobs can still run a preview flagged as such.
4. Embed job text.
5. Retrieve candidate set (AuthZ scope).
6. Optional ANN prefilter on profile vectors.
7. Full matching + features + scores + explanations for remaining set.
8. Ranker orders list; UI shows current, potential, gaps.
9. Recruiter shortlist/reject/compare → `recruiter_decisions` (training labels).
10. Analytics views read runs + decisions.

---

## 19. Training pipeline

Training is an **offline CLI** (`python -m ml.train`), not an HTTP handler.

```
1. Snapshot labels + features
2. Join match feature_snapshots to labels (point-in-time: features from before the decision)
3. Train/val/test split (by job_id or org_id — must be decided to prevent leakage)
4. Train XGBoost
5. Evaluate (§21)
6. Write artifact + metrics + feature_schema checksum
7. Register ml_models status=candidate
8. Human (admin) activates after review
```

### 19.1 Leakage rules

- Do not use post-decision features.
- Do not split randomly if multiple candidates share a job: prefer **GroupKFold by job_id**.
- Do not train on test jobs used in the report’s final numbers.

### 19.2 Cold start

Until N labeled decisions exist (threshold is a team decision; see §D), skip training. CI can run `ml.train` on a **synthetic fixture** only to test the **plumbing**, never to report accuracy as a project result.

### 19.3 Reproducibility

Pin: git SHA, ontology_version, embedding model name, feature_schema_version, XGBoost params, data snapshot id.

---

## 20. Model inference pipeline

```
load active artifact once
validate feature_schema_version == extractor.schema_version
else refuse trained mode and fall back to baseline (log loudly)
```

Per match:

1. Build features.
2. If `RANKER_IMPL=xgboost` and schema matches: `predict_proba` / relevance.
3. Calibrate if a calibrator artifact exists.
4. Compose DTO (current from interpretable formula; potential from model or baseline).
5. SHAP optional (can be sampled if too slow).
6. Persist run.

Latency budget (college hardware): full score of one pair < 200 ms excluding NLP/embed. NLP/embed are async.

---

## 21. Model evaluation pipeline

Evaluation is mandatory before calling a model “trained” in the UI.

### 21.1 Offline (required)

Depends on target type:

| Target | Metrics |
|---|---|
| Binary (shortlist/hire) | ROC-AUC, PR-AUC, Brier, recall@k, precision@k |
| Graded relevance | NDCG@k, MAP |
| Regression | MAE, Spearman vs expert score |

**Always** compare to:

- Random ranker
- Required-skill exact-match baseline
- Full baseline composer (§10.2) **without** XGBoost

A trained model that loses to the baseline on the held-out set **must not** be activated.

### 21.2 Error analysis

Slice by seniority, gap size, job family. Report ontology coverage of those slices.

### 21.3 No-data policy

If there is no labeled test set, the report must say so. Demo the baseline. Do not quote imaginary AUC.

### 21.4 Extraction evaluation (separate)

Skill/section extraction uses a **small gold set of resumes** annotated by the team. Metrics: precision/recall of canonical skills, sectioning accuracy. This is NLP eval, not ranker eval.

---

## 22. Feedback loop

```
Recruiter actions → recruiter_decisions
Candidate apply/save → candidate_decisions
Periodic snapshot → training set
Train → candidate model → evaluation → activate or reject
Match_runs store model_version so analytics can compare eras
```

**Human-in-the-loop:** recruiters correcting extracted skills and required skills improve NLP/ontology, which improves features, which improves ML. Treat ontology edits as first-class feedback, not only shortlists.

**Drift:** if shortlist rate vs predicted probability diverges, admin dashboard flags; do not auto-retrain without evaluation.

**Bias watch:** even without protected attributes, proxies (college name, gaps in employment) can leak. Document limitation; avoid encoding institution prestige as a feature unless the team explicitly justifies it.

---

## 23. Security considerations

| Area | Control |
|---|---|
| Auth | Argon2id, httpOnly refresh, CSRF/Origin on cookies, in-memory rate limit on login |
| AuthZ | RBAC + org scope on every resource |
| Uploads | MIME + magic bytes, size cap, no executable, store outside web root |
| PII | Minimize; encrypt disk in production; TLS; no PII in logs or training notebooks committed to git |
| Secrets | Env / secret manager; never in frontend |
| Injection | SQLAlchemy params; no raw SQL concatenation; sanitize filenames |
| Path traversal | Content-addressed storage keys |
| Model | Artifact checksum; only admin activates; schema mismatch → baseline fallback |
| Fairness | No protected attributes in features; document residual proxy risk |
| Availability | Timeouts on parse/embed; job retries with backoff |
| LLM (if added later) | Traces-only prompt; no raw PII to third-party APIs unless policy allows |

College residual risks: no WAF, limited virus scanning, single-region deploy. State these in the report.

---

## 24. Testing strategy

| Layer | Tool | What |
|---|---|---|
| Unit | Pytest | Ontology policy, normalization, feature math, current/potential formulas, AuthZ helpers |
| NLP fixtures | Pytest | Golden resumes/JDs (anonymized) → expected canonical skills |
| API | Pytest + httpx | OpenAPI contract, role isolation, upload limits |
| ML plumbing | Pytest | Feature schema round-trip, leakage split helper, refuse mismatched artifact |
| ML quality | Pytest + scripts | Only run if fixture dataset present; never hardcode “AUC > 0.9” |
| E2E | Playwright | Candidate upload→confirm→see ranked jobs; recruiter job→rank→shortlist |
| Frontend | Component tests optional | Explanation renderer for each trace type |

CI (GitHub Actions): lint + unit + API tests on PR. Playwright on main or nightly. Training is **not** in PR CI except a 1-second dummy XGBoost on synthetic rows to verify import/train/serialize.

---

## 25. Deployment architecture

**Dev:** Docker Compose — `web`, `api`, `db` (Postgres+pgvector). Local volume for blobs and Sentence-Transformers cache.

**Prod (college / VM):** same compose or a single VM: Caddy/Nginx TLS → web static + api. Managed Postgres if available.

```
GitHub Actions: test → build images → (optional) deploy
```

**Models & encoders:** mounted volume or object storage; not baked into frontend images. API image may include a default MiniLM for offline labs.

**No Kubernetes** unless the institute already requires it. Overkill for this project.

**Env:** `DATABASE_URL`, `JWT_SECRET`, `RANKER_IMPL`, `EMBEDDING_MODEL`, `BLOB_ROOT`, `MAX_RESUME_BYTES`, `DOCUMENT_PARSER_VERSION`, `NLP_PIPELINE_VERSION`, `ONTOLOGY_DEFAULT_VERSION`, `ONTOLOGY_FUZZY_THRESHOLD`.

---

## 26. Development phases

| Phase | Goal | Intelligence mode |
|---|---|---|
| 0 | Monorepo, Compose, CI, OpenAPI skeleton, auth | None |
| 1 | Users, orgs, jobs CRUD, resume upload storage | None |
| 2 | NLP extract + profile confirm UI | Deterministic NLP |
| 3 | Ontology seed, normalization, admin editor | Rules |
| 4 | Embeddings + semantic features | Semantic similarity |
| 5 | Matching policy, current match, explanations, gaps | Baseline ranking |
| 6 | Potential baseline, career path, two-way ranking | Baseline potential |
| 7 | Recruiter compare/shortlist, analytics views | Label collection starts |
| 8 | Feature snapshots, training CLI, eval scripts | Plumbing only |
| 9 | Train XGBoost **if labels exist**; SHAP; model registry | Trained (or remain baseline) |
| 10 | Hardening, Playwright, report, SDG write-up | Production-ready demo |

Phases 0–10 are sufficient for a defensible demo **without** claiming project model accuracy, provided the report is honest when labeled data is insufficient.

Implementation tracking in this repo currently maps **Phase 3** to document I/O, **Phase 4** to §6 NLP extraction (`nlp-v1`), **Phase 5** to §7–§8 ontology (`seed-0.1`), **Phase 6** to §9 embeddings (`embedding-text-v1`), **Phase 7** to baseline matching (`feature-schema-v1`), **Phase 8** to heuristic potential (`feature-schema-v2`, `docs/POTENTIAL.md`), **Phase 9** to recruiter decisions and dataset snapshots (`docs/DATASET.md`), and **Phase 10** to offline XGBoost training (`docs/ML_TRAINING.md`). See `docs/MATCHING.md`.

---

## 27. Risks and technical challenges

1. **No labels / no dataset** — cannot train XGBoost credibly. Mitigation: strong baseline + label capture from day one of recruiter UI.
2. **Resume PDF quality** — two-column layouts, tables, scans. Mitigation: candidate confirm; OCR optional; don’t hide parse failures.
3. **Ontology incompleteness** — unmatched skills look like gaps. Mitigation: admin review queue; fuzzy match with caution; coverage metric.
4. **Hierarchy policy errors** — treating parent as child mastery. Mitigation: unit tests in §8.3.
5. **Leakage in ML splits** — inflated metrics. Mitigation: group by job_id; point-in-time features.
6. **Embedding model change** — silent score drift. Mitigation: version vectors; full reindex.
7. **Latency** — embed-on-request. Mitigation: async jobs; persist vectors.
8. **Fairness / SDG tension** — ranking people. Mitigation: no protected attributes; explainability; human shortlist.
9. **Scope creep** — chatbot, generic ATS, LLM ranker. Mitigation: this document.
10. **Team bandwidth** — 3 user types + ML + NLP. Mitigation: phases 0–7 first; shared talent-pool decision early.
11. **Legal** — storing resumes. Mitigation: consent, deletion, institute ethics if human raters used.

---

## 28. Recommended repository structure

```
Ai-based-recuritment-recommendation-engine/
  README.md
  docker-compose.yml
  .github/workflows/ci.yml
  docs/
    ARCHITECTURE.md          # this file
    API.md                   # generated later from OpenAPI
    ONTOLOGY.md              # matching policy + seed notes
    ML.md                    # target variable, split rules, once decided
  frontend/                  # Next.js app
    app/
    components/
    lib/
    e2e/                     # Playwright
  backend/
    app/                     # FastAPI modular monolith
    tests/
    alembic/
    pyproject.toml
  ml/
    train.py
    evaluate.py
    features/                # shared with backend via package or copy-boundaried module
    artifacts/               # gitignored
    tests/
  ontology/
    seed/                    # YAML/JSON skills, aliases, relations
    scripts/                 # load_seed.py
  storage/                   # local blobs gitignored
  scripts/                   # dev bootstrap
```

**Shared Python:** prefer `backend/app/modules/features` imported by `ml/` via installable package (`pip install -e backend`) so training and serving cannot drift.

Do **not** add Nx/Turborepo unless the team already knows them.

---

# A. Final recommended architecture

**Modular monolith:** Next.js UI + FastAPI domain modules + PostgreSQL/pgvector + local object storage.

**Four-layer intelligence stack:**

1. Deterministic NLP + skill normalization  
2. Curated skill ontology (hierarchy, aliases, relatedness)  
3. Frozen Sentence-Transformers similarities  
4. Interpretable current-match composer + potential scorer (rules first, XGBoost when labels exist)

**Differentiator:** current match vs potential, both explainable via structured traces; ranking is two-way (jobs↔candidates); ML is a replaceable module behind the same DTO.

**Not in core:** LLM ranker, microservices, invented accuracy, assumed public dataset.

---

# B. Recommended repository / folder structure

See §28. Top-level: `frontend/`, `backend/`, `ml/`, `ontology/`, `docs/`, Compose, GitHub Actions.

---

# C. Development phases in order

0 Infra/auth → 1 CRUD/upload → 2 NLP/profile → 3 Ontology → 4 Embeddings → 5 Baseline match + explanations → 6 Potential + career path → 7 Recruiter decisions + analytics → 8 Training plumbing → 9 Train/evaluate/activate **if data** → 10 Harden and report.

---

# D. Decisions that must be finalized before ML training

1. **Target variable** — shortlist, hire, expert grade, or pairwise preference?  
2. **Positive/negative definition** — is “viewed but not shortlisted” a negative, or unknown?  
3. **Split strategy** — GroupKFold by `job_id` vs `org_id` vs time.  
4. **Population** — applicants only vs opted-in pool.  
5. **Feature freeze** — `feature_schema_v1` locked before first reported experiment.  
6. **Embedding model + ontology version** pinned for the training snapshot.  
7. **Evaluation metrics + k** for recall@k / NDCG@k.  
8. **Activation bar** — must beat which baseline by how much?  
9. **Ethics** — consent for using decisions as labels; no protected attributes.  
10. **Dataset construction** — product logs vs team-annotated gold vs licensed public data (none assumed).

Until these are written in `docs/ML.md`, do not train for the final report.

---

# E. Potential technical risks

See §27. Highest: **label scarcity**, **PDF extraction**, **ontology coverage**, **train/test leakage**, **scope creep toward chatbot/ATS**.

---

# F. Questions the team must answer before implementation

1. Is the talent pool **org-private** (applicants only) or a **shared campus pool**?  
2. English-only resumes? Any OCR requirement?  
3. Which embedding model is the lab default (CPU RAM limits)?  
4. Who owns ontology curation (one student) and what is the v1 skill domain boundary (e.g. software roles only)?  
5. Will recruiters **confirm** extracted JD requirements before ranking goes live?  
6. Default sort: current match or balanced? Who can toggle weights?  
7. What is a “hire” in this project — real internships, mock recruiters, or faculty raters?  
8. Are public ontologies (ESCO/O*NET) in scope legally and time-wise, or curated-only?  
9. Minimum labeled decisions before attempting XGBoost (e.g. 200? 500?)?  
10. Should education institution names be a feature, or excluded as a prestige proxy?  
11. Deployment target: lab Docker Compose only, or a public URL for viva?  
12. Data retention after the semester ends?

---

*PRJ_385 architecture — planning document. Implementation starts only after the team answers §F and records §D in `docs/ML.md`.*
