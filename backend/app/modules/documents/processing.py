"""Resume parse job runner.

Phase 3 executes `resume_parse` in-process after upload. The same entry point can
later be called from a worker without changing routers.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import ExtractionRevision, Resume
from app.models.enums import ParseStatus, ProcessingJobStatus
from app.modules.documents.constants import parser_version
from app.modules.documents.processor import extract_document
from app.modules.documents.repository import DocumentRepository, mark_processing
from app.modules.documents.storage import BlobStore
from app.modules.identity import audit
from app.modules.identity.tokens import utcnow

RESUME_PARSE_STARTED = "resume_parse_started"
RESUME_PARSE_COMPLETED = "resume_parse_completed"
RESUME_PARSE_FAILED = "resume_parse_failed"


class ResumeParseProcessor:
    """Processes `processing_jobs.type = resume_parse`."""

    def __init__(self, db: Session, blobs: BlobStore, repo: DocumentRepository) -> None:
        self.db = db
        self.blobs = blobs
        self.repo = repo

    def enqueue_and_run(self, resume: Resume, *, kind: str, actor_id: uuid.UUID) -> None:
        """Create a queued job, then run it. A future worker can replace the run step."""
        self.run(resume, kind=kind, actor_id=actor_id)

    def run(self, resume: Resume, *, kind: str, actor_id: uuid.UUID) -> None:
        job = self.repo.new_parse_job(resume.id, resume.candidate_id)
        mark_processing(job, resume)
        audit.record_audit(
            self.db,
            action=RESUME_PARSE_STARTED,
            resource_type="resume",
            actor_user_id=actor_id,
            resource_id=resume.id,
            metadata={"job_id": str(job.id), "type": "resume_parse"},
        )
        self.db.flush()
        data = self._read_blob(resume)
        if data is None:
            resume.parse_status = ParseStatus.FAILED.value
            job.status = ProcessingJobStatus.FAILED.value
            job.error = "Stored document is missing."
            job.finished_at = utcnow()
            audit.record_audit(
                self.db,
                action=RESUME_PARSE_FAILED,
                resource_type="resume",
                actor_user_id=actor_id,
                resource_id=resume.id,
                metadata={"reason": "missing_blob"},
            )
            self.db.flush()
            return
        outcome = extract_document(kind=kind, data=data)
        now = utcnow()
        if outcome.status == ParseStatus.READY.value:
            revision = ExtractionRevision(
                resume_id=resume.id,
                revision_number=self.repo.next_revision_number(resume.id),
                parser_version=parser_version(),
                extraction_payload=outcome.payload,
            )
            self.repo.add_revision(revision)
            if revision not in resume.extraction_revisions:
                resume.extraction_revisions.append(revision)
            resume.parse_status = ParseStatus.READY.value
            resume.parsed_at = now
            job.status = ProcessingJobStatus.COMPLETED.value
            job.finished_at = now
            audit.record_audit(
                self.db,
                action=RESUME_PARSE_COMPLETED,
                resource_type="resume",
                actor_user_id=actor_id,
                resource_id=resume.id,
                metadata={"status": "ready", "parser_version": parser_version()},
            )
        elif outcome.status == ParseStatus.NEEDS_OCR.value:
            revision = ExtractionRevision(
                resume_id=resume.id,
                revision_number=self.repo.next_revision_number(resume.id),
                parser_version=parser_version(),
                extraction_payload=outcome.payload,
            )
            self.repo.add_revision(revision)
            if revision not in resume.extraction_revisions:
                resume.extraction_revisions.append(revision)
            resume.parse_status = ParseStatus.NEEDS_OCR.value
            resume.parsed_at = now
            job.status = ProcessingJobStatus.COMPLETED.value
            job.error = outcome.error
            job.finished_at = now
            audit.record_audit(
                self.db,
                action=RESUME_PARSE_COMPLETED,
                resource_type="resume",
                actor_user_id=actor_id,
                resource_id=resume.id,
                metadata={"status": "needs_ocr"},
            )
        else:
            resume.parse_status = ParseStatus.FAILED.value
            job.status = ProcessingJobStatus.FAILED.value
            job.error = (outcome.error or "Parse failed.")[:4000]
            job.finished_at = now
            audit.record_audit(
                self.db,
                action=RESUME_PARSE_FAILED,
                resource_type="resume",
                actor_user_id=actor_id,
                resource_id=resume.id,
                metadata={"reason": "parse_failed"},
            )
        self.db.flush()
        if outcome.status == ParseStatus.READY.value:
            try:
                with self.db.begin_nested():
                    from app.modules.nlp.service import NlpService

                    NlpService(self.db).extract_resume(resume, actor_id=actor_id)
            except Exception:
                audit.record_audit(
                    self.db,
                    action="nlp_failed",
                    resource_type="resume",
                    actor_user_id=actor_id,
                    resource_id=resume.id,
                    metadata={"reason": "pipeline_error"},
                )
            else:
                try:
                    with self.db.begin_nested():
                        from app.modules.ontology.service import OntologyService

                        OntologyService(self.db).annotate_latest_draft(resume.candidate_id)
                except Exception:
                    audit.record_audit(
                        self.db,
                        action="ontology_failed",
                        resource_type="resume",
                        actor_user_id=actor_id,
                        resource_id=resume.id,
                        metadata={"reason": "normalize_error"},
                    )

    def _read_blob(self, resume: Resume) -> bytes | None:
        try:
            return self.blobs.get(resume.storage_key)
        except FileNotFoundError:
            return None
        except OSError:
            return None
