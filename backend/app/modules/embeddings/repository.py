"""pgvector persistence for embeddings. Does not rank candidates."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CandidateProfile,
    CandidateSkill,
    Embedding,
    ExperienceItem,
    ExtractionRevision,
    Job,
    JobPreferredSkill,
    JobRequiredSkill,
    JobRequirement,
    ProcessingJob,
    ProjectItem,
    Resume,
)
from app.models.enums import ConfirmationStatus
from app.modules.embeddings.compatibility import EncoderIdentity
from app.modules.embeddings.constants import CHUNK_FULL


class EmbeddingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile(self, profile_id: uuid.UUID) -> CandidateProfile | None:
        return self.db.scalar(
            select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.experience_items),
                selectinload(CandidateProfile.education_items),
                selectinload(CandidateProfile.project_items),
                selectinload(CandidateProfile.certification_items),
                selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
            )
            .where(CandidateProfile.id == profile_id)
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

    def get_experience(self, experience_id: uuid.UUID) -> ExperienceItem | None:
        return self.db.get(ExperienceItem, experience_id)

    def get_project(self, project_id: uuid.UUID) -> ProjectItem | None:
        return self.db.get(ProjectItem, project_id)

    def get_revision(self, revision_id: uuid.UUID) -> ExtractionRevision | None:
        return self.db.get(ExtractionRevision, revision_id)

    def get_resume(self, resume_id: uuid.UUID) -> Resume | None:
        return self.db.scalar(select(Resume).where(Resume.id == resume_id, Resume.deleted_at.is_(None)))

    def get_embedding(
        self,
        *,
        owner_type: str,
        owner_id: uuid.UUID,
        chunk_type: str,
        identity: EncoderIdentity,
    ) -> Embedding | None:
        return self.db.scalar(
            select(Embedding).where(
                Embedding.owner_type == owner_type,
                Embedding.owner_id == owner_id,
                Embedding.chunk_type == chunk_type,
                Embedding.model_name == identity.model_name,
                Embedding.model_version == identity.model_version,
                Embedding.embedding_text_version == identity.embedding_text_version,
            )
        )

    def get_embedding_by_id(self, embedding_id: uuid.UUID) -> Embedding | None:
        return self.db.get(Embedding, embedding_id)

    def latest_owner_embedding(
        self, owner_type: str, owner_id: uuid.UUID, chunk_type: str = CHUNK_FULL
    ) -> Embedding | None:
        return self.db.scalar(
            select(Embedding)
            .where(
                Embedding.owner_type == owner_type,
                Embedding.owner_id == owner_id,
                Embedding.chunk_type == chunk_type,
            )
            .order_by(Embedding.created_at.desc())
            .limit(1)
        )

    def upsert(self, row: Embedding) -> Embedding:
        self.db.add(row)
        self.db.flush()
        return row

    def add_job(self, job: ProcessingJob) -> ProcessingJob:
        self.db.add(job)
        self.db.flush()
        return job

    def similar(
        self,
        *,
        query: list[float],
        identity: EncoderIdentity,
        owner_type: str,
        limit: int,
    ) -> list[tuple[Embedding, float]]:
        distance = Embedding.vector.cosine_distance(query)
        stmt = (
            select(Embedding, (1 - distance).label("similarity"))
            .where(
                Embedding.owner_type == owner_type,
                Embedding.model_name == identity.model_name,
                Embedding.model_version == identity.model_version,
                Embedding.dimensions == identity.dimensions,
                Embedding.embedding_text_version == identity.embedding_text_version,
            )
            .order_by(distance)
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [(row[0], float(row[1])) for row in rows]
