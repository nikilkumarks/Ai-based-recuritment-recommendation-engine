# Skill ontology

The ontology is the source of aliases, hierarchy, and relatedness. **Skill normalization is not candidate-job matching.**

V1 is a **curated, limited CS/IT catalog** (`seed-0.1`). It is not complete and is not inferred from resumes.

## What this phase does

- Canonical skills in `skills`
- Aliases in `skill_aliases` (aliases are not skills)
- Directed `parent_of` plus undirected `related_to` / `similar_to` in `skill_relations`
- Immutable snapshots in `ontology_versions.graph_snapshot`
- Deterministic `resolve_skill(mention, ontology_version)`
- Normalized results on profile/job drafts, then `candidate_skills` / `job_*_skills` on confirm

It does **not** embed text, score candidates, or train models.

## Resolution order

1. Exact canonical name (after lookup normalization)
2. Exact alias string
3. Normalized alias
4. Gated RapidFuzz fallback (unique hit ≥ threshold; ambiguous → unmatched)
5. `unmatched` / needs review — never invent a canonical skill

Lookup normalization preserves `C++`, `C#`, `.NET`, `Node.js`, `Next.js`, `CI/CD`, `scikit-learn`.

`extraction_confidence`, `normalization_confidence`, and future `match_score` are different fields.

## Hierarchy policy

| Job requires | Candidate has | Evidence type | Meaning |
|---|---|---|---|
| Machine Learning | ML (alias) | exact (same canonical ID) | Canonical match |
| Machine Learning | Deep Learning | child | Partial/related evidence, **not** mastery of ML |
| Deep Learning | Machine Learning | parent | Weak/parent evidence, **not** Deep Learning |
| Kubernetes | Docker | related | Related skill, **not** equivalent |

`parent_of` is stored in one direction. `child_of` is derived. Cycles are rejected.

## Seed

```bash
python scripts/seed_ontology.py
```

Idempotent. Activates `seed-0.1`. Admin mutations change the live catalog; resolution uses the **active snapshot** until a new version is published (`POST /api/v1/admin/ontology/versions`).

## Admin

All `/api/v1/admin/ontology/*` routes require an admin account (admins are not self-registered). Candidates and recruiters cannot mutate the ontology.
