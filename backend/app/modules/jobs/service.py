"""Recruiter job description NLP and requirement confirmation."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models import Job, JobRequirement, User
from app.models.enums import ConfirmationStatus, JobStatus, UserRole
from app.modules.authorization.service import AuthorizationService
from app.modules.identity import audit
from app.modules.jobs.schemas import (
    JobCreate,
    JobDetail,
    JobListResponse,
    JobRequirementUpdate,
    JobRequirementView,
    JobSummary,
)
from app.modules.nlp.repository import NlpRepository
from app.modules.nlp.schemas import JobRequirementsDraft
from app.modules.nlp.service import NlpService
from app.modules.ontology.schemas import SkillNormalizationResult
from app.modules.ontology.service import OntologyService

JOB_CREATED = "job_created"
JOB_REQUIREMENTS_UPDATED = "job_requirements_updated"
JOB_REQUIREMENTS_CONFIRMED = "job_requirements_confirmed"
logger = logging.getLogger("prj385.jobs")


class JobService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.authz = AuthorizationService(db)
        self.repo = NlpRepository(db)
        self.nlp = NlpService(db)
        self.ontology = OntologyService(db)

    def _org_id(self, user: User, requested: uuid.UUID | None) -> uuid.UUID:
        self.authz.require_roles(user, UserRole.RECRUITER.value, UserRole.ADMIN.value)
        org_ids = self.authz.recruiter_organization_ids(user)
        if user.role == UserRole.ADMIN.value and requested is not None:
            return requested
        if not org_ids:
            raise ForbiddenError("You are not a member of an organization.")
        if requested is None:
            return org_ids[0]
        if requested not in org_ids and user.role != UserRole.ADMIN.value:
            raise ForbiddenError("You do not have permission to access this organization.")
        return requested

    def create_job(self, *, user: User, payload: JobCreate) -> JobDetail:
        org_id = self._org_id(user, payload.organization_id)
        self.authz.require_org_member(user, org_id)
        job = Job(
            organization_id=org_id,
            created_by=user.id,
            title=payload.title,
            description_raw=payload.description_raw,
            location=payload.location,
            employment_type=payload.employment_type,
            seniority=payload.seniority,
            status=JobStatus.DRAFT.value,
        )
        self.repo.add_job(job)
        audit.record_audit(
            self.db,
            action=JOB_CREATED,
            resource_type="job",
            actor_user_id=user.id,
            resource_id=job.id,
            metadata={"organization_id": str(org_id)},
        )
        try:
            self.nlp.extract_job(job.id, actor_id=user.id)
            requirement = self.repo.latest_requirement(job.id)
            if requirement is not None:
                self.ontology.annotate_job_requirement(requirement)
        except Exception:
            logger.exception("Job NLP failed; job row was kept without a draft")
        self.db.flush()
        return self.get_job(user=user, job_id=job.id)

    def list_jobs(self, *, user: User) -> JobListResponse:
        org_id = self._org_id(user, None)
        items = [
            JobSummary(
                id=job.id,
                title=job.title,
                status=job.status,
                organization_id=job.organization_id,
                created_at=job.created_at,
            )
            for job in self.repo.list_jobs(org_id)
        ]
        return JobListResponse(items=items)

    def get_job(self, *, user: User, job_id: uuid.UUID) -> JobDetail:
        job = self.authz.require_job_org_access(user, job_id)
        requirement = self.repo.latest_requirement(job.id)
        return JobDetail(
            id=job.id,
            title=job.title,
            description_raw=job.description_raw,
            status=job.status,
            location=job.location,
            employment_type=job.employment_type,
            seniority=job.seniority,
            organization_id=job.organization_id,
            requirements=_requirement_view(requirement) if requirement else None,
        )

    def extract(self, *, user: User, job_id: uuid.UUID) -> JobRequirementView:
        self.authz.require_job_org_access(user, job_id)
        self.nlp.extract_job(job_id, actor_id=user.id)
        requirement = self.repo.latest_requirement(job_id)
        if requirement is None:
            raise ConflictError("Job extraction did not produce requirements.")
        self.ontology.annotate_job_requirement(requirement)
        return _requirement_view(requirement)

    def update_requirements(
        self, *, user: User, job_id: uuid.UUID, payload: JobRequirementUpdate
    ) -> JobRequirementView:
        self.authz.require_job_org_access(user, job_id)
        requirement = self._editable_requirement(job_id)
        data = dict(requirement.extracted_payload or {})
        mapping = {
            "title": payload.title,
            "required_skills": payload.required_skills,
            "preferred_skills": payload.preferred_skills,
            "min_years_experience": payload.min_years_experience,
            "education_level": payload.education_level,
            "seniority": payload.seniority,
            "location": payload.location,
            "employment_type": payload.employment_type,
        }
        for key, value in mapping.items():
            if value is not None:
                data[key] = value
                if key == "min_years_experience":
                    requirement.min_years_experience = value
                if key == "education_level":
                    requirement.education_level = value
        requirement.extracted_payload = data
        flag_modified(requirement, "extracted_payload")
        if payload.required_skills is not None or payload.preferred_skills is not None:
            self.ontology.annotate_job_requirement(requirement)
        audit.record_audit(
            self.db,
            action=JOB_REQUIREMENTS_UPDATED,
            resource_type="job_requirement",
            actor_user_id=user.id,
            resource_id=requirement.id,
            metadata={"job_id": str(job_id)},
        )
        self.db.flush()
        return _requirement_view(requirement)

    def confirm(self, *, user: User, job_id: uuid.UUID) -> JobRequirementView:
        job = self.authz.require_job_org_access(user, job_id)
        requirement = self.repo.latest_requirement(job_id)
        if requirement is None or requirement.confirmation_status != ConfirmationStatus.DRAFT.value:
            raise ConflictError("There is no draft job requirement to confirm.")
        data = requirement.extracted_payload or {}
        if data.get("location"):
            job.location = str(data["location"])[:255]
        if data.get("employment_type"):
            job.employment_type = str(data["employment_type"])[:64]
        if data.get("seniority"):
            job.seniority = str(data["seniority"])[:64]
        if data.get("title"):
            job.title = str(data["title"])[:255]
        self.ontology.persist_confirmed_job_skills(requirement)
        requirement.confirmation_status = ConfirmationStatus.CONFIRMED.value
        audit.record_audit(
            self.db,
            action=JOB_REQUIREMENTS_CONFIRMED,
            resource_type="job_requirement",
            actor_user_id=user.id,
            resource_id=requirement.id,
            metadata={"job_id": str(job_id)},
        )
        self.db.flush()
        return _requirement_view(requirement)

    def _editable_requirement(self, job_id: uuid.UUID) -> JobRequirement:
        current = self.repo.latest_requirement(job_id)
        if current is None:
            raise NotFoundError("No extracted job requirements exist yet.")
        if current.confirmation_status == ConfirmationStatus.DRAFT.value:
            return current
        copy = JobRequirement(
            job_id=job_id,
            min_years_experience=current.min_years_experience,
            education_level=current.education_level,
            confirmation_status=ConfirmationStatus.DRAFT.value,
            parser_version=current.parser_version,
            extracted_payload=dict(current.extracted_payload or {}),
        )
        return self.repo.add_requirement(copy)


def _requirement_view(requirement: JobRequirement) -> JobRequirementView:
    draft = None
    payload = requirement.extracted_payload or {}
    try:
        if payload:
            draft = JobRequirementsDraft.model_validate(payload)
    except Exception:
        draft = None
    years = requirement.min_years_experience
    return JobRequirementView(
        id=requirement.id,
        job_id=requirement.job_id,
        confirmation_status=requirement.confirmation_status,
        parser_version=requirement.parser_version,
        min_years_experience=float(years) if years is not None else None,
        education_level=requirement.education_level,
        ontology_version=payload.get("ontology_version"),
        draft=draft,
        normalized_required_skills=_normalized(payload.get("normalized_required_skills")),
        normalized_preferred_skills=_normalized(payload.get("normalized_preferred_skills")),
    )


def _normalized(rows) -> list[SkillNormalizationResult]:
    items: list[SkillNormalizationResult] = []
    for item in rows or []:
        try:
            items.append(SkillNormalizationResult.model_validate(item))
        except Exception:
            continue
    return items
