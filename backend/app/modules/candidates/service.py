"""Candidate profile confirmation. Confirmed rows are the future matching source of truth."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.errors import ConflictError, NotFoundError
from app.models import (
    CandidateProfile,
    CertificationItem,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    User,
)
from app.models.enums import ConfirmationStatus
from app.modules.authorization.service import AuthorizationService
from app.modules.candidates.schemas import ProfileResponse, ProfileUpdate, ProfileView
from app.modules.identity import audit
from app.modules.identity.tokens import utcnow
from app.modules.nlp.repository import NlpRepository
from app.modules.nlp.schemas import ProfileDraft
from app.modules.nlp.service import NlpService
from app.modules.ontology.schemas import SkillNormalizationResult
from app.modules.ontology.service import OntologyService

PROFILE_UPDATED = "profile_updated"
PROFILE_CONFIRMED = "profile_confirmed"


class CandidateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.authz = AuthorizationService(db)
        self.repo = NlpRepository(db)
        self.nlp = NlpService(db)
        self.ontology = OntologyService(db)

    def require_owner(self, user: User, candidate_id: uuid.UUID) -> None:
        self.authz.require_candidate_owner(user, candidate_id)

    def get_profile(self, *, user: User, candidate_id: uuid.UUID) -> ProfileResponse:
        self.require_owner(user, candidate_id)
        confirmed = self.repo.latest_profile(candidate_id, status=ConfirmationStatus.CONFIRMED.value)
        draft = self.repo.latest_profile(candidate_id, status=ConfirmationStatus.DRAFT.value)
        return ProfileResponse(
            confirmed=_to_view(confirmed) if confirmed else None,
            draft=_to_view(draft) if draft else None,
        )

    def update_draft(self, *, user: User, candidate_id: uuid.UUID, payload: ProfileUpdate) -> ProfileView:
        self.require_owner(user, candidate_id)
        draft = self._editable_draft(candidate_id)
        data = dict(draft.extracted_payload or {})
        fields = ("summary", "skills", "experience", "education", "projects", "certifications", "contact")
        for field in fields:
            value = getattr(payload, field)
            if value is not None:
                if field == "summary":
                    draft.summary = value
                    data["summary"] = value
                else:
                    data[field] = value
        draft.extracted_payload = data
        flag_modified(draft, "extracted_payload")
        if payload.skills is not None:
            self.ontology.annotate_profile(draft)
        audit.record_audit(
            self.db,
            action=PROFILE_UPDATED,
            resource_type="candidate_profile",
            actor_user_id=user.id,
            resource_id=draft.id,
            metadata={"profile_version": draft.profile_version},
        )
        self.db.flush()
        return _to_view(draft)

    def confirm(self, *, user: User, candidate_id: uuid.UUID) -> ProfileView:
        self.require_owner(user, candidate_id)
        draft = self.repo.latest_profile(candidate_id, status=ConfirmationStatus.DRAFT.value)
        if draft is None:
            raise ConflictError("There is no draft profile to confirm.")
        self._write_items(draft)
        self.ontology.persist_confirmed_profile_skills(draft)
        draft.confirmation_status = ConfirmationStatus.CONFIRMED.value
        draft.confirmed_at = utcnow()
        audit.record_audit(
            self.db,
            action=PROFILE_CONFIRMED,
            resource_type="candidate_profile",
            actor_user_id=user.id,
            resource_id=draft.id,
            metadata={"profile_version": draft.profile_version},
        )
        self.db.flush()
        return _to_view(draft)

    def rerun_resume_nlp(self, *, user: User, candidate_id: uuid.UUID, resume_id: uuid.UUID) -> ProfileView:
        self.require_owner(user, candidate_id)
        resume = self.repo.get_resume(resume_id)
        if resume is None or resume.candidate_id != candidate_id:
            raise NotFoundError("Resume not found.")
        draft = self.nlp.extract_resume(resume, actor_id=user.id)
        if draft is None:
            raise ConflictError("NLP could not produce a profile draft from this resume.")
        stored = self.repo.latest_profile(candidate_id, status=ConfirmationStatus.DRAFT.value)
        if stored is None:
            raise ConflictError("NLP finished but no draft profile was stored.")
        self.ontology.annotate_profile(stored)
        return _to_view(stored)

    def _editable_draft(self, candidate_id: uuid.UUID) -> CandidateProfile:
        draft = self.repo.latest_profile(candidate_id, status=ConfirmationStatus.DRAFT.value)
        if draft is not None:
            return draft
        confirmed = self.repo.latest_profile(candidate_id, status=ConfirmationStatus.CONFIRMED.value)
        if confirmed is None:
            raise NotFoundError("No profile draft exists yet. Upload a resume first.")
        copy = CandidateProfile(
            candidate_id=candidate_id,
            source_revision_id=confirmed.source_revision_id,
            profile_version=self.repo.max_profile_version(candidate_id) + 1,
            summary=confirmed.summary,
            confirmation_status=ConfirmationStatus.DRAFT.value,
            extracted_payload=dict(confirmed.extracted_payload or {}),
        )
        return self.repo.add_profile(copy)

    def _write_items(self, profile: CandidateProfile) -> None:
        payload = profile.extracted_payload or {}
        experience = [
            _experience_row(profile.id, row)
            for row in payload.get("experience") or []
            if row.get("job_title")
        ]
        education = [
            _education_row(profile.id, row)
            for row in payload.get("education") or []
            if row.get("institution")
        ]
        projects = [_project_row(profile.id, row) for row in payload.get("projects") or [] if row.get("name")]
        certifications = [
            _cert_row(profile.id, row) for row in payload.get("certifications") or [] if row.get("name")
        ]
        self.repo.replace_profile_items(
            profile,
            experience=experience,
            education=education,
            projects=projects,
            certifications=certifications,
        )


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _experience_row(profile_id: uuid.UUID, row: dict) -> ExperienceItem:
    return ExperienceItem(
        candidate_profile_id=profile_id,
        job_title=str(row.get("job_title") or "Unknown"),
        employer=row.get("employer"),
        description=row.get("description"),
        start_date=_parse_date(row.get("start_date")),
        end_date=_parse_date(row.get("end_date")),
        is_current=bool(row.get("is_current")),
        years_experience=row.get("years_experience"),
        evidence={"source": "nlp_confirm", "raw": row.get("evidence") or []},
    )


def _education_row(profile_id: uuid.UUID, row: dict) -> EducationItem:
    return EducationItem(
        candidate_profile_id=profile_id,
        institution=str(row.get("institution") or "Unknown"),
        degree=row.get("degree"),
        field_of_study=row.get("field_of_study"),
        start_date=_parse_date(row.get("start_date")),
        end_date=_parse_date(row.get("end_date")),
        education_level=row.get("education_level"),
        description=None,
    )


def _project_row(profile_id: uuid.UUID, row: dict) -> ProjectItem:
    return ProjectItem(
        candidate_profile_id=profile_id,
        name=str(row.get("name") or "Untitled project"),
        description=row.get("description"),
        url=row.get("url"),
        start_date=_parse_date(row.get("start_date")),
        end_date=_parse_date(row.get("end_date")),
    )


def _cert_row(profile_id: uuid.UUID, row: dict) -> CertificationItem:
    return CertificationItem(
        candidate_profile_id=profile_id,
        name=str(row.get("name") or "Certification"),
        issuing_organization=row.get("issuing_organization"),
        issue_date=_parse_date(row.get("issue_date")),
        expiry_date=_parse_date(row.get("expiry_date")),
        credential_url=row.get("credential_url"),
    )


def _to_view(profile: CandidateProfile) -> ProfileView:
    payload = profile.extracted_payload or {}
    draft = None
    try:
        if payload:
            draft = ProfileDraft.model_validate(payload)
    except Exception:
        draft = None
    return ProfileView(
        id=profile.id,
        profile_version=profile.profile_version,
        confirmation_status=profile.confirmation_status,
        summary=profile.summary,
        confirmed_at=profile.confirmed_at,
        source_revision_id=profile.source_revision_id,
        nlp_pipeline_version=payload.get("nlp_pipeline_version"),
        ontology_version=payload.get("ontology_version"),
        draft=draft,
        normalized_skills=_normalized_skills(payload),
        experience=[
            {
                "job_title": item.job_title,
                "employer": item.employer,
                "description": item.description,
                "start_date": item.start_date.isoformat() if item.start_date else None,
                "end_date": item.end_date.isoformat() if item.end_date else None,
                "is_current": item.is_current,
            }
            for item in profile.experience_items
        ],
        education=[
            {
                "institution": item.institution,
                "degree": item.degree,
                "field_of_study": item.field_of_study,
                "education_level": item.education_level,
            }
            for item in profile.education_items
        ],
        projects=[
            {"name": item.name, "description": item.description, "url": item.url}
            for item in profile.project_items
        ],
        certifications=[
            {"name": item.name, "issuing_organization": item.issuing_organization}
            for item in profile.certification_items
        ],
    )


def _normalized_skills(payload: dict) -> list[SkillNormalizationResult]:
    rows = []
    for item in payload.get("normalized_skills") or []:
        try:
            rows.append(SkillNormalizationResult.model_validate(item))
        except Exception:
            continue
    return rows

