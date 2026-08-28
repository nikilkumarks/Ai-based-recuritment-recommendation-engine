"""Persistence for NLP drafts on candidate profiles and job requirements."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CandidateProfile,
    CertificationItem,
    EducationItem,
    ExperienceItem,
    ExtractionRevision,
    Job,
    JobRequirement,
    ProcessingJob,
    ProjectItem,
    Resume,
)
from app.models.enums import ProcessingJobStatus, ProcessingJobType
from app.modules.identity.tokens import utcnow


class NlpRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_resume(self, resume_id: uuid.UUID) -> Resume | None:
        return self.db.scalar(
            select(Resume)
            .options(selectinload(Resume.extraction_revisions))
            .where(Resume.id == resume_id, Resume.deleted_at.is_(None))
        )

    def get_revision(self, revision_id: uuid.UUID) -> ExtractionRevision | None:
        return self.db.get(ExtractionRevision, revision_id)

    def latest_revision(self, resume: Resume) -> ExtractionRevision | None:
        if not resume.extraction_revisions:
            return None
        return max(resume.extraction_revisions, key=lambda row: row.revision_number)

    def latest_profile(
        self, candidate_id: uuid.UUID, *, status: str | None = None
    ) -> CandidateProfile | None:
        stmt = (
            select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.experience_items),
                selectinload(CandidateProfile.education_items),
                selectinload(CandidateProfile.project_items),
                selectinload(CandidateProfile.certification_items),
                selectinload(CandidateProfile.skills),
            )
            .where(CandidateProfile.candidate_id == candidate_id)
            .order_by(CandidateProfile.profile_version.desc())
        )
        if status is not None:
            stmt = stmt.where(CandidateProfile.confirmation_status == status)
        return self.db.scalar(stmt.limit(1))

    def max_profile_version(self, candidate_id: uuid.UUID) -> int:
        current = self.db.scalar(
            select(func.max(CandidateProfile.profile_version)).where(
                CandidateProfile.candidate_id == candidate_id
            )
        )
        return int(current or 0)

    def add_profile(self, profile: CandidateProfile) -> CandidateProfile:
        self.db.add(profile)
        self.db.flush()
        return profile

    def get_profile(self, profile_id: uuid.UUID) -> CandidateProfile | None:
        return self.db.scalar(
            select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.experience_items),
                selectinload(CandidateProfile.education_items),
                selectinload(CandidateProfile.project_items),
                selectinload(CandidateProfile.certification_items),
                selectinload(CandidateProfile.skills),
            )
            .where(CandidateProfile.id == profile_id)
        )

    def replace_profile_items(
        self,
        profile: CandidateProfile,
        *,
        experience: list[ExperienceItem],
        education: list[EducationItem],
        projects: list[ProjectItem],
        certifications: list[CertificationItem],
    ) -> None:
        self.db.execute(delete(ExperienceItem).where(ExperienceItem.candidate_profile_id == profile.id))
        self.db.execute(delete(EducationItem).where(EducationItem.candidate_profile_id == profile.id))
        self.db.execute(delete(ProjectItem).where(ProjectItem.candidate_profile_id == profile.id))
        self.db.execute(delete(CertificationItem).where(CertificationItem.candidate_profile_id == profile.id))
        for item in (*experience, *education, *projects, *certifications):
            self.db.add(item)
        self.db.flush()

    def get_job(self, job_id: uuid.UUID) -> Job | None:
        return self.db.scalar(
            select(Job).options(selectinload(Job.requirements)).where(Job.id == job_id)
        )

    def list_jobs(self, organization_id: uuid.UUID) -> list[Job]:
        return list(
            self.db.scalars(
                select(Job)
                .options(selectinload(Job.requirements))
                .where(Job.organization_id == organization_id)
                .order_by(Job.created_at.desc())
            ).all()
        )

    def add_job(self, job: Job) -> Job:
        self.db.add(job)
        self.db.flush()
        return job

    def latest_requirement(self, job_id: uuid.UUID) -> JobRequirement | None:
        return self.db.scalar(
            select(JobRequirement)
            .where(JobRequirement.job_id == job_id)
            .order_by(JobRequirement.created_at.desc())
            .limit(1)
        )

    def add_requirement(self, requirement: JobRequirement) -> JobRequirement:
        self.db.add(requirement)
        self.db.flush()
        return requirement

    def add_resume_nlp_job(self, resume_id: uuid.UUID, candidate_id: uuid.UUID) -> ProcessingJob:
        job = ProcessingJob(
            type=ProcessingJobType.RESUME_NLP.value,
            status=ProcessingJobStatus.QUEUED.value,
            payload={"resume_id": str(resume_id), "candidate_id": str(candidate_id)},
        )
        self.db.add(job)
        self.db.flush()
        return job

    def add_job_parse(self, job_id: uuid.UUID) -> ProcessingJob:
        job = ProcessingJob(
            type=ProcessingJobType.JOB_PARSE.value,
            status=ProcessingJobStatus.QUEUED.value,
            payload={"job_id": str(job_id)},
        )
        self.db.add(job)
        self.db.flush()
        return job

    def mark_job_parse_done(self, job: ProcessingJob, *, ok: bool, error: str | None = None) -> None:
        now = utcnow()
        job.started_at = job.started_at or now
        job.finished_at = now
        job.status = ProcessingJobStatus.COMPLETED.value if ok else ProcessingJobStatus.FAILED.value
        job.error = (error or "")[:4000] or None
