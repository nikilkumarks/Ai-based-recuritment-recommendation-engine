"""Persistence for match runs, feature snapshots, and visible candidate/job sets."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Candidate,
    CandidateProfile,
    CandidateSkill,
    Embedding,
    FeatureSnapshot,
    Job,
    JobPreferredSkill,
    JobRequiredSkill,
    JobRequirement,
    MatchExplanation,
    MatchRun,
    Skill,
)
from app.models.enums import ConfirmationStatus, EmbeddingOwnerType, JobStatus
from app.modules.embeddings.constants import CHUNK_FULL

HIDDEN_JOB_STATUSES = (
    JobStatus.CLOSED.value,
    JobStatus.ARCHIVED.value,
    JobStatus.PAUSED.value,
)


class MatchingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_candidate(self, candidate_id: uuid.UUID) -> Candidate | None:
        return self.db.scalar(
            select(Candidate).options(selectinload(Candidate.user)).where(Candidate.id == candidate_id)
        )

    def list_candidates(self) -> list[Candidate]:
        return list(
            self.db.scalars(select(Candidate).options(selectinload(Candidate.user)).order_by(Candidate.created_at)).all()
        )

    def latest_confirmed_profile(self, candidate_id: uuid.UUID) -> CandidateProfile | None:
        return self.db.scalar(
            select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.experience_items),
                selectinload(CandidateProfile.education_items),
                selectinload(CandidateProfile.project_items),
                selectinload(CandidateProfile.certification_items),
                selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
            )
            .where(
                CandidateProfile.candidate_id == candidate_id,
                CandidateProfile.confirmation_status == ConfirmationStatus.CONFIRMED.value,
            )
            .order_by(CandidateProfile.profile_version.desc())
            .limit(1)
        )

    def get_job(self, job_id: uuid.UUID) -> Job | None:
        return self.db.scalar(
            select(Job)
            .options(
                selectinload(Job.requirements)
                .selectinload(JobRequirement.required_skills)
                .selectinload(JobRequiredSkill.skill),
                selectinload(Job.requirements)
                .selectinload(JobRequirement.preferred_skills)
                .selectinload(JobPreferredSkill.skill),
            )
            .where(Job.id == job_id)
        )

    def latest_confirmed_requirement(self, job: Job) -> JobRequirement | None:
        confirmed = [
            row for row in job.requirements if row.confirmation_status == ConfirmationStatus.CONFIRMED.value
        ]
        if not confirmed:
            return None
        return max(confirmed, key=lambda row: row.created_at)

    def list_visible_jobs(self) -> list[Job]:
        confirmed_ids = select(JobRequirement.job_id).where(
            JobRequirement.confirmation_status == ConfirmationStatus.CONFIRMED.value
        )
        return list(
            self.db.scalars(
                select(Job)
                .options(
                    selectinload(Job.requirements)
                    .selectinload(JobRequirement.required_skills)
                    .selectinload(JobRequiredSkill.skill),
                    selectinload(Job.requirements)
                    .selectinload(JobRequirement.preferred_skills)
                    .selectinload(JobPreferredSkill.skill),
                )
                .where(Job.id.in_(confirmed_ids), Job.status.notin_(HIDDEN_JOB_STATUSES))
                .order_by(Job.created_at.desc())
            ).all()
        )

    def get_skill(self, skill_id: uuid.UUID) -> Skill | None:
        return self.db.get(Skill, skill_id)

    def latest_owner_embedding(self, owner_type: str, owner_id: uuid.UUID) -> Embedding | None:
        return self.db.scalar(
            select(Embedding)
            .where(
                Embedding.owner_type == owner_type,
                Embedding.owner_id == owner_id,
                Embedding.chunk_type == CHUNK_FULL,
            )
            .order_by(Embedding.created_at.desc())
            .limit(1)
        )

    def latest_embeddings_for_owners(
        self, owner_type: str, owner_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Embedding]:
        if not owner_ids:
            return {}
        rows = list(
            self.db.scalars(
                select(Embedding)
                .where(
                    Embedding.owner_type == owner_type,
                    Embedding.owner_id.in_(owner_ids),
                    Embedding.chunk_type == CHUNK_FULL,
                )
                .order_by(Embedding.created_at.desc())
            ).all()
        )
        latest: dict[uuid.UUID, Embedding] = {}
        for row in rows:
            latest.setdefault(row.owner_id, row)
        return latest

    def persist_run(
        self,
        *,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
        ontology_version_id: uuid.UUID | None,
        feature_schema_version: str,
        weight_set_version: str,
        current_match: float,
        potential: float | None,
        semantic_similarity: float | None,
        project_relevance: float | None,
        experience_relevance: float | None,
        features: dict[str, Any],
        traces: list[dict[str, Any]],
        scoring_mode: str = "baseline",
        model_version: str | None = None,
    ) -> MatchRun:
        stamped = datetime.now(timezone.utc)
        run = MatchRun(
            candidate_id=candidate_id,
            job_id=job_id,
            scoring_mode=scoring_mode,
            model_version=model_version,
            ontology_version_id=ontology_version_id,
            feature_schema_version=feature_schema_version,
            weight_set_version=weight_set_version,
            current_match=round(current_match, 2),
            potential=None if potential is None else round(potential, 2),
            semantic_similarity=semantic_similarity,
            project_relevance=project_relevance,
            experience_relevance=experience_relevance,
            feature_snapshot=features,
            unconfirmed_profile=False,
            created_at=stamped,
        )
        self.db.add(run)
        self.db.flush()
        self.db.add(
            FeatureSnapshot(
                match_run_id=run.id,
                feature_schema_version=feature_schema_version,
                features=features,
                created_at=stamped,
            )
        )
        self.db.add(MatchExplanation(match_run_id=run.id, traces=traces, created_at=stamped))
        self.db.flush()
        return run

    def count_candidate_skills(self, profile_id: uuid.UUID) -> int:
        return len(
            list(
                self.db.scalars(
                    select(CandidateSkill).where(CandidateSkill.candidate_profile_id == profile_id)
                ).all()
            )
        )

    def count_match_runs(self, candidate_id: uuid.UUID, job_id: uuid.UUID) -> int:
        rows = self.db.scalars(
            select(MatchRun.id).where(MatchRun.candidate_id == candidate_id, MatchRun.job_id == job_id)
        ).all()
        return len(list(rows))


PROFILE_OWNER = EmbeddingOwnerType.PROFILE.value
JOB_OWNER = EmbeddingOwnerType.JOB.value
PROJECT_OWNER = EmbeddingOwnerType.PROJECT.value
EXPERIENCE_OWNER = EmbeddingOwnerType.EXPERIENCE.value
