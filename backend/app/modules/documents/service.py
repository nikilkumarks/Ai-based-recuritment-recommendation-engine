"""Resume upload, parse orchestration, and deletion. Routers stay thin."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models import Resume, User
from app.models.enums import ParseStatus, UserRole
from app.modules.authorization.service import AuthorizationService
from app.modules.documents.processing import ResumeParseProcessor
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import ResumeSummary, resume_to_summary
from app.modules.documents.storage import BlobStore, resume_storage_key, sha256_hex
from app.modules.documents.validators import ValidatedUpload
from app.modules.identity import audit

RESUME_UPLOADED = "resume_uploaded"
RESUME_DELETED = "resume_deleted"


class DocumentService:
    def __init__(self, db: Session, blob_store: BlobStore) -> None:
        self.db = db
        self.blobs = blob_store
        self.repo = DocumentRepository(db)
        self.authz = AuthorizationService(db)
        self.parser = ResumeParseProcessor(db, blob_store, self.repo)

    def require_owner(self, user: User, candidate_id: uuid.UUID) -> None:
        self.authz.require_candidate_owner(user, candidate_id)

    def require_read(self, user: User, candidate_id: uuid.UUID) -> None:
        if user.role == UserRole.CANDIDATE.value:
            self.authz.require_candidate_owner(user, candidate_id)
            return
        if user.role in {UserRole.RECRUITER.value, UserRole.ADMIN.value}:
            self.authz.require_recruiter_candidate_scope(user, candidate_id)
            return
        raise ForbiddenError("You do not have permission to access this candidate.")

    def upload(self, *, user: User, candidate_id: uuid.UUID, upload: ValidatedUpload) -> ResumeSummary:
        self.require_owner(user, candidate_id)
        digest = sha256_hex(upload.data)
        existing = self.repo.find_duplicate(candidate_id, digest)
        if existing is not None:
            if existing.parse_status in {ParseStatus.FAILED.value, ParseStatus.NEEDS_OCR.value}:
                self.parser.enqueue_and_run(existing, kind=upload.kind, actor_id=user.id)
            audit.record_audit(
                self.db,
                action=RESUME_UPLOADED,
                resource_type="resume",
                actor_user_id=user.id,
                resource_id=existing.id,
                metadata={"duplicate": True, "sha256": digest, "mime_type": upload.mime_type},
            )
            self.db.flush()
            return resume_to_summary(existing, duplicate=True, latest_parser_version=_parser_of(existing))

        key = resume_storage_key(digest)
        self.blobs.put(key, upload.data)
        resume = Resume(
            candidate_id=candidate_id,
            storage_key=key,
            original_filename=upload.filename,
            mime_type=upload.mime_type,
            file_size=len(upload.data),
            sha256=digest,
            parse_status=ParseStatus.QUEUED.value,
        )
        self.repo.add_resume(resume)
        audit.record_audit(
            self.db,
            action=RESUME_UPLOADED,
            resource_type="resume",
            actor_user_id=user.id,
            resource_id=resume.id,
            metadata={"duplicate": False, "sha256": digest, "mime_type": upload.mime_type},
        )
        self.db.flush()
        self.parser.enqueue_and_run(resume, kind=upload.kind, actor_id=user.id)
        return resume_to_summary(resume, latest_parser_version=_parser_of(resume))

    def list_resumes(self, *, user: User, candidate_id: uuid.UUID) -> list[ResumeSummary]:
        self.require_read(user, candidate_id)
        return [
            resume_to_summary(row, latest_parser_version=_parser_of(row))
            for row in self.repo.list_resumes(candidate_id)
        ]

    def get_resume(self, *, user: User, candidate_id: uuid.UUID, resume_id: uuid.UUID) -> ResumeSummary:
        self.require_read(user, candidate_id)
        resume = self.repo.get_resume_for_candidate(candidate_id, resume_id)
        if resume is None:
            raise NotFoundError("Resume not found.")
        return resume_to_summary(resume, latest_parser_version=_parser_of(resume))

    def delete_resume(self, *, user: User, candidate_id: uuid.UUID, resume_id: uuid.UUID) -> None:
        self.require_owner(user, candidate_id)
        resume = self.repo.get_resume_for_candidate(candidate_id, resume_id)
        if resume is None:
            raise NotFoundError("Resume not found.")
        digest = resume.sha256
        key = resume.storage_key
        self.repo.delete_resume(resume)
        remaining = self.repo.count_by_sha256(digest)
        if remaining == 0:
            self.blobs.delete(key)
        audit.record_audit(
            self.db,
            action=RESUME_DELETED,
            resource_type="resume",
            actor_user_id=user.id,
            resource_id=resume_id,
            metadata={"sha256": digest},
        )
        self.db.flush()


def _parser_of(resume: Resume) -> str | None:
    if not resume.extraction_revisions:
        return None
    latest = max(resume.extraction_revisions, key=lambda row: row.revision_number)
    return latest.parser_version
