"""Run NLP after document extraction and persist drafts. No ML imports."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import CandidateProfile, ExtractionRevision, JobRequirement, Resume
from app.models.enums import ConfirmationStatus
from app.modules.identity import audit
from app.modules.nlp.constants import nlp_version
from app.modules.nlp.pipeline import extract_job_draft, extract_profile_draft
from app.modules.nlp.repository import NlpRepository
from app.modules.nlp.schemas import JobRequirementsDraft, ProfileDraft

logger = logging.getLogger("prj385.nlp")

NLP_STARTED = "nlp_started"
NLP_COMPLETED = "nlp_completed"
NLP_FAILED = "nlp_failed"


class NlpService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = NlpRepository(db)

    def extract_resume(self, resume: Resume, *, actor_id: uuid.UUID | None) -> ProfileDraft | None:
        revision = self.repo.latest_revision(resume)
        if revision is None:
            return None
        nlp_job = self.repo.add_resume_nlp_job(resume.id, resume.candidate_id)
        text = str((revision.extraction_payload or {}).get("normalized_text") or "")
        audit.record_audit(
            self.db,
            action=NLP_STARTED,
            resource_type="resume",
            actor_user_id=actor_id,
            resource_id=resume.id,
            metadata={"pipeline": nlp_version()},
        )
        if not text.strip():
            self._store_nlp(
                revision,
                {"status": "skipped", "reason": "empty_text", "pipeline_version": nlp_version()},
            )
            self.repo.mark_job_parse_done(nlp_job, ok=True, error="empty_text")
            return None
        try:
            draft = extract_profile_draft(text, parser_version=revision.parser_version)
        except Exception:
            logger.exception("NLP resume extraction failed")
            self._store_nlp(
                revision,
                {"status": "failed", "pipeline_version": nlp_version(), "error": "Extraction failed safely."},
            )
            self.repo.mark_job_parse_done(nlp_job, ok=False, error="Extraction failed safely.")
            audit.record_audit(
                self.db,
                action=NLP_FAILED,
                resource_type="resume",
                actor_user_id=actor_id,
                resource_id=resume.id,
                metadata={"reason": "extract_failed"},
            )
            return None
        self._store_nlp(
            revision,
            {
                "status": "ready",
                "pipeline_version": draft.nlp_pipeline_version,
                "profile_draft": draft.model_dump(mode="json"),
            },
        )
        self._upsert_draft_profile(resume.candidate_id, revision, draft)
        audit.record_audit(
            self.db,
            action=NLP_COMPLETED,
            resource_type="resume",
            actor_user_id=actor_id,
            resource_id=resume.id,
            metadata={"status": "ready", "pipeline": draft.nlp_pipeline_version},
        )
        self.repo.mark_job_parse_done(nlp_job, ok=True)
        self.db.flush()
        return draft

    def extract_job(self, job_id: uuid.UUID, *, actor_id: uuid.UUID | None) -> JobRequirementsDraft:
        job = self.repo.get_job(job_id)
        if job is None:
            raise LookupError("Job not found.")
        parse_job = self.repo.add_job_parse(job.id)
        self.repo.mark_job_parse_done(parse_job, ok=True)
        audit.record_audit(
            self.db,
            action=NLP_STARTED,
            resource_type="job",
            actor_user_id=actor_id,
            resource_id=job.id,
            metadata={"pipeline": nlp_version(), "type": "job_parse"},
        )
        try:
            draft = extract_job_draft(job.description_raw, fallback_title=job.title)
        except Exception:
            logger.exception("NLP job extraction failed")
            self.repo.mark_job_parse_done(parse_job, ok=False, error="Extraction failed safely.")
            audit.record_audit(
                self.db,
                action=NLP_FAILED,
                resource_type="job",
                actor_user_id=actor_id,
                resource_id=job.id,
                metadata={"reason": "extract_failed"},
            )
            raise
        existing = self.repo.latest_requirement(job.id)
        if existing is None or existing.confirmation_status == ConfirmationStatus.CONFIRMED.value:
            requirement = JobRequirement(
                job_id=job.id,
                min_years_experience=draft.min_years_experience,
                education_level=draft.education_level,
                confirmation_status=ConfirmationStatus.DRAFT.value,
                parser_version=draft.nlp_pipeline_version,
                extracted_payload=draft.model_dump(mode="json"),
            )
            self.repo.add_requirement(requirement)
        else:
            existing.min_years_experience = draft.min_years_experience
            existing.education_level = draft.education_level
            existing.parser_version = draft.nlp_pipeline_version
            existing.extracted_payload = draft.model_dump(mode="json")
            flag_modified(existing, "extracted_payload")
        audit.record_audit(
            self.db,
            action=NLP_COMPLETED,
            resource_type="job",
            actor_user_id=actor_id,
            resource_id=job.id,
            metadata={"status": "ready", "pipeline": draft.nlp_pipeline_version},
        )
        self.db.flush()
        return draft

    def _store_nlp(self, revision: ExtractionRevision, nlp_payload: dict) -> None:
        payload = dict(revision.extraction_payload or {})
        payload["nlp"] = nlp_payload
        revision.extraction_payload = payload
        flag_modified(revision, "extraction_payload")
        self.db.flush()

    def _upsert_draft_profile(
        self, candidate_id: uuid.UUID, revision: ExtractionRevision, draft: ProfileDraft
    ) -> CandidateProfile:
        current_draft = self.repo.latest_profile(candidate_id, status=ConfirmationStatus.DRAFT.value)
        payload = draft.model_dump(mode="json")
        if current_draft is not None:
            current_draft.summary = draft.summary
            current_draft.source_revision_id = revision.id
            current_draft.extracted_payload = payload
            flag_modified(current_draft, "extracted_payload")
            self.db.flush()
            return current_draft
        profile = CandidateProfile(
            candidate_id=candidate_id,
            source_revision_id=revision.id,
            profile_version=self.repo.max_profile_version(candidate_id) + 1,
            summary=draft.summary,
            confirmation_status=ConfirmationStatus.DRAFT.value,
            extracted_payload=payload,
        )
        return self.repo.add_profile(profile)
