"""Database access for resumes, extraction revisions, and parse jobs."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Candidate, Embedding, ExtractionRevision, ProcessingJob, Resume
from app.models.enums import EmbeddingOwnerType, ParseStatus, ProcessingJobStatus, ProcessingJobType
from app.modules.identity.tokens import utcnow


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_candidate(self, candidate_id: uuid.UUID) -> Candidate | None:
        return self.db.scalar(select(Candidate).where(Candidate.id == candidate_id))

    def get_resume(self, resume_id: uuid.UUID) -> Resume | None:
        return self.db.scalar(
            select(Resume)
            .options(selectinload(Resume.extraction_revisions))
            .where(Resume.id == resume_id)
        )

    def get_resume_for_candidate(self, candidate_id: uuid.UUID, resume_id: uuid.UUID) -> Resume | None:
        return self.db.scalar(
            select(Resume)
            .options(selectinload(Resume.extraction_revisions))
            .where(
                Resume.id == resume_id,
                Resume.candidate_id == candidate_id,
                Resume.deleted_at.is_(None),
            )
        )

    def list_resumes(self, candidate_id: uuid.UUID) -> list[Resume]:
        return list(
            self.db.scalars(
                select(Resume)
                .options(selectinload(Resume.extraction_revisions))
                .where(Resume.candidate_id == candidate_id, Resume.deleted_at.is_(None))
                .order_by(Resume.created_at.desc())
            ).all()
        )

    def find_duplicate(self, candidate_id: uuid.UUID, digest: str) -> Resume | None:
        return self.db.scalar(
            select(Resume)
            .options(selectinload(Resume.extraction_revisions))
            .where(
                Resume.candidate_id == candidate_id,
                Resume.sha256 == digest,
                Resume.deleted_at.is_(None),
            )
            .order_by(Resume.created_at.asc())
            .limit(1)
        )

    def count_by_sha256(self, digest: str) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(Resume).where(
                    Resume.sha256 == digest,
                    Resume.deleted_at.is_(None),
                )
            )
            or 0
        )

    def add_resume(self, resume: Resume) -> Resume:
        self.db.add(resume)
        self.db.flush()
        return resume

    def add_job(self, job: ProcessingJob) -> ProcessingJob:
        self.db.add(job)
        self.db.flush()
        return job

    def get_job(self, job_id: uuid.UUID) -> ProcessingJob | None:
        return self.db.get(ProcessingJob, job_id)

    def next_revision_number(self, resume_id: uuid.UUID) -> int:
        current = self.db.scalar(
            select(func.max(ExtractionRevision.revision_number)).where(
                ExtractionRevision.resume_id == resume_id
            )
        )
        return int(current or 0) + 1

    def add_revision(self, revision: ExtractionRevision) -> ExtractionRevision:
        self.db.add(revision)
        self.db.flush()
        return revision

    def latest_revision(self, resume: Resume) -> ExtractionRevision | None:
        if resume.extraction_revisions:
            return max(resume.extraction_revisions, key=lambda row: row.revision_number)
        return None

    def delete_resume(self, resume: Resume) -> None:
        self.db.execute(
            delete(Embedding).where(
                Embedding.owner_type == EmbeddingOwnerType.RESUME_CHUNK.value,
                Embedding.owner_id == resume.id,
            )
        )
        self.db.execute(delete(Resume).where(Resume.id == resume.id))
        self.db.flush()

    def new_parse_job(self, resume_id: uuid.UUID, candidate_id: uuid.UUID) -> ProcessingJob:
        job = ProcessingJob(
            type=ProcessingJobType.RESUME_PARSE.value,
            status=ProcessingJobStatus.QUEUED.value,
            payload={"resume_id": str(resume_id), "candidate_id": str(candidate_id)},
        )
        return self.add_job(job)


def mark_processing(job: ProcessingJob, resume: Resume) -> None:
    now = utcnow()
    job.status = ProcessingJobStatus.PROCESSING.value
    job.started_at = now
    resume.parse_status = ParseStatus.PROCESSING.value
