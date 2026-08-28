"""Idempotent curated ontology seed. Does not invent skills from resumes."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from app.models import OntologyVersion, Skill, SkillAlias, SkillRelation
from app.models.enums import AliasSource, OntologyVersionStatus, SkillRelationType, SkillStatus
from app.modules.identity.tokens import utcnow
from app.modules.ontology.catalog import (
    ALIASES,
    PARENT_EDGES,
    RELATED_EDGES,
    SEED_VERSION,
    SIMILAR_EDGES,
    SKILLS,
)
from app.modules.ontology.normalize import normalize_lookup
from app.modules.ontology.repository import OntologyRepository
from app.modules.ontology.validation import parent_cycles


def seed_ontology(db: Session) -> OntologyVersion:
    """Insert the V1 CS/IT catalog. Safe to run twice."""
    repo = OntologyRepository(db)
    by_slug: dict[str, Skill] = {}
    for name, slug, category, description in SKILLS:
        skill = repo.skill_by_slug(slug)
        if skill is None:
            skill = repo.add_skill(
                Skill(
                    canonical_name=name,
                    slug=slug,
                    category=category,
                    description=description,
                    status=SkillStatus.ACTIVE.value,
                )
            )
        by_slug[slug] = skill
    db.flush()
    for slug, aliases in ALIASES.items():
        skill = by_slug[slug]
        for alias in aliases:
            normalized = normalize_lookup(alias)
            if not normalized:
                continue
            if normalized == normalize_lookup(skill.canonical_name):
                continue
            if repo.alias_by_normalized(normalized) is None:
                repo.add_alias(
                    SkillAlias(
                        skill_id=skill.id,
                        alias=alias,
                        normalized_alias=normalized,
                        source=AliasSource.CURATED.value,
                    )
                )
    for parent_slug, child_slug in PARENT_EDGES:
        _edge(repo, by_slug[parent_slug], by_slug[child_slug], SkillRelationType.PARENT_OF.value)
    for left, right in RELATED_EDGES:
        _edge(repo, by_slug[left], by_slug[right], SkillRelationType.RELATED_TO.value)
    for left, right in SIMILAR_EDGES:
        _edge(repo, by_slug[left], by_slug[right], SkillRelationType.SIMILAR_TO.value)
    cycles = parent_cycles(
        [(by_slug[parent].id, by_slug[child].id) for parent, child in PARENT_EDGES]
    )
    if cycles:
        raise RuntimeError(cycles[0])
    snapshot = repo.snapshot_payload()
    checksum = _checksum(snapshot)
    existing = repo.version_by_name(SEED_VERSION)
    if existing is None:
        row = OntologyVersion(
            version=SEED_VERSION,
            checksum=checksum,
            status=OntologyVersionStatus.ACTIVE.value,
            activated_at=utcnow(),
            graph_snapshot=snapshot,
        )
        repo.add_version(row)
        db.flush()
        return row
    if existing.graph_snapshot is None:
        existing.graph_snapshot = snapshot
        existing.checksum = checksum
    if existing.status != OntologyVersionStatus.ACTIVE.value and repo.active_version() is None:
        existing.status = OntologyVersionStatus.ACTIVE.value
        existing.activated_at = utcnow()
    db.flush()
    return existing


def _edge(repo: OntologyRepository, source: Skill, target: Skill, relation: str) -> None:
    if repo.relation_edge(source.id, target.id, relation) is None:
        repo.add_relation(
            SkillRelation(
                source_skill_id=source.id,
                target_skill_id=target.id,
                relation=relation,
                weight=1,
            )
        )


def _checksum(snapshot: dict) -> str:
    payload = json.dumps(snapshot, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
