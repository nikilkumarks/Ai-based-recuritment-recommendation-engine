"""Persistence for skills, aliases, relations, and ontology versions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CandidateProfile,
    CandidateSkill,
    JobPreferredSkill,
    JobRequiredSkill,
    JobRequirement,
    OntologyVersion,
    Skill,
    SkillAlias,
    SkillRelation,
)
from app.models.enums import OntologyVersionStatus, SkillStatus


class OntologyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_skill(self, skill_id: uuid.UUID) -> Skill | None:
        return self.db.get(Skill, skill_id)

    def skill_by_slug(self, slug: str) -> Skill | None:
        return self.db.scalar(select(Skill).where(Skill.slug == slug))

    def skill_by_name(self, name: str) -> Skill | None:
        return self.db.scalar(select(Skill).where(Skill.canonical_name == name))

    def list_skills(self) -> list[Skill]:
        return list(self.db.scalars(select(Skill).order_by(Skill.canonical_name)).all())

    def add_skill(self, skill: Skill) -> Skill:
        self.db.add(skill)
        self.db.flush()
        return skill

    def alias_by_normalized(self, normalized: str) -> SkillAlias | None:
        return self.db.scalar(select(SkillAlias).where(SkillAlias.normalized_alias == normalized))

    def add_alias(self, alias: SkillAlias) -> SkillAlias:
        self.db.add(alias)
        self.db.flush()
        return alias

    def relation_edge(
        self, source_id: uuid.UUID, target_id: uuid.UUID, relation: str
    ) -> SkillRelation | None:
        return self.db.scalar(
            select(SkillRelation).where(
                SkillRelation.source_skill_id == source_id,
                SkillRelation.target_skill_id == target_id,
                SkillRelation.relation == relation,
            )
        )

    def add_relation(self, relation: SkillRelation) -> SkillRelation:
        self.db.add(relation)
        self.db.flush()
        return relation

    def list_relations(self) -> list[SkillRelation]:
        return list(self.db.scalars(select(SkillRelation)).all())

    def list_aliases(self) -> list[SkillAlias]:
        return list(self.db.scalars(select(SkillAlias)).all())

    def active_skills_and_graph(self) -> tuple[list[Skill], list[SkillAlias], list[SkillRelation]]:
        skills = list(
            self.db.scalars(select(Skill).where(Skill.status == SkillStatus.ACTIVE.value)).all()
        )
        aliases = list(self.db.scalars(select(SkillAlias)).all())
        relations = list(self.db.scalars(select(SkillRelation)).all())
        return skills, aliases, relations

    def version_by_name(self, version: str) -> OntologyVersion | None:
        return self.db.scalar(select(OntologyVersion).where(OntologyVersion.version == version))

    def active_version(self) -> OntologyVersion | None:
        return self.db.scalar(
            select(OntologyVersion).where(OntologyVersion.status == OntologyVersionStatus.ACTIVE.value)
        )

    def list_versions(self) -> list[OntologyVersion]:
        return list(self.db.scalars(select(OntologyVersion).order_by(OntologyVersion.created_at)).all())

    def add_version(self, row: OntologyVersion) -> OntologyVersion:
        self.db.add(row)
        self.db.flush()
        return row

    def retire_active(self) -> None:
        current = self.active_version()
        if current is not None:
            current.status = OntologyVersionStatus.RETIRED.value

    def get_profile(self, profile_id: uuid.UUID) -> CandidateProfile | None:
        return self.db.scalar(
            select(CandidateProfile)
            .options(selectinload(CandidateProfile.skills))
            .where(CandidateProfile.id == profile_id)
        )

    def replace_candidate_skills(self, profile: CandidateProfile, rows: list[CandidateSkill]) -> None:
        self.db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_profile_id == profile.id))
        for row in rows:
            self.db.add(row)
        self.db.flush()

    def get_requirement(self, requirement_id: uuid.UUID) -> JobRequirement | None:
        return self.db.scalar(
            select(JobRequirement)
            .options(
                selectinload(JobRequirement.required_skills),
                selectinload(JobRequirement.preferred_skills),
            )
            .where(JobRequirement.id == requirement_id)
        )

    def replace_job_skills(
        self,
        requirement: JobRequirement,
        *,
        required: list[JobRequiredSkill],
        preferred: list[JobPreferredSkill],
    ) -> None:
        self.db.execute(
            delete(JobRequiredSkill).where(JobRequiredSkill.job_requirement_id == requirement.id)
        )
        self.db.execute(
            delete(JobPreferredSkill).where(JobPreferredSkill.job_requirement_id == requirement.id)
        )
        for row in (*required, *preferred):
            self.db.add(row)
        self.db.flush()

    def snapshot_payload(self) -> dict[str, Any]:
        skills, aliases, relations = self.active_skills_and_graph()
        return {
            "skills": [
                {
                    "id": str(item.id),
                    "canonical_name": item.canonical_name,
                    "slug": item.slug,
                    "status": item.status,
                    "category": item.category,
                }
                for item in skills
            ],
            "aliases": [
                {
                    "skill_id": str(item.skill_id),
                    "alias": item.alias,
                    "normalized_alias": item.normalized_alias,
                }
                for item in aliases
            ],
            "relations": [
                {
                    "source_skill_id": str(item.source_skill_id),
                    "target_skill_id": str(item.target_skill_id),
                    "relation": item.relation,
                    "weight": float(item.weight),
                }
                for item in relations
            ],
        }
