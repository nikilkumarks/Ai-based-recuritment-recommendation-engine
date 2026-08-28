"""Embedding lifecycle. Semantic features only — not ranking or recruitment scores."""

from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models import Embedding, Job, ProcessingJob, User
from app.models.enums import (
    ConfirmationStatus,
    EmbeddingOwnerType,
    ProcessingJobStatus,
    ProcessingJobType,
    UserRole,
)
from app.modules.authorization.service import AuthorizationService
from app.modules.embeddings.chunker import chunks_from_payload
from app.modules.embeddings.compatibility import (
    EncoderIdentity,
    classify_status,
    identity_from_row,
    require_compatible,
)
from app.modules.embeddings.constants import CHUNK_FULL
from app.modules.embeddings.encoder import Encoder, get_encoder
from app.modules.embeddings.hashing import content_hash
from app.modules.embeddings.repository import EmbeddingRepository
from app.modules.embeddings.schemas import EmbeddingStatus, SimilarityRequest, SimilarityResponse
from app.modules.embeddings.similarity import cosine_similarity, require_dimension
from app.modules.embeddings.text_builder import (
    build_experience_text,
    build_job_requirement_text,
    build_job_text,
    build_profile_text,
    build_project_text,
    text_version,
)
from app.modules.identity import audit
from app.modules.identity.tokens import utcnow

logger = logging.getLogger("prj385.embeddings")


class EmbeddingService:
    def __init__(self, db: Session, encoder: Encoder | None = None) -> None:
        self.db = db
        self.authz = AuthorizationService(db)
        self.repo = EmbeddingRepository(db)
        self.encoder = encoder or get_encoder()

    def encoder_identity(self) -> EncoderIdentity:
        return self.encoder.identity(text_version())

    def profile_status(self, *, user: User, candidate_id: uuid.UUID) -> EmbeddingStatus:
        self.authz.require_candidate_owner(user, candidate_id)
        profile = self.repo.latest_confirmed_profile(candidate_id)
        if profile is None:
            raise ConflictError("A confirmed profile is required before embedding.")
        return self._status(
            owner_type=EmbeddingOwnerType.PROFILE.value,
            owner_id=profile.id,
            text=build_profile_text(profile),
        )

    def job_status(self, *, user: User, job_id: uuid.UUID) -> EmbeddingStatus:
        self.authz.require_job_org_access(user, job_id)
        job = self.repo.get_job(job_id)
        if job is None:
            raise NotFoundError("Job not found.")
        requirement = _latest_confirmed_requirement(job)
        if requirement is None:
            raise ConflictError("Confirmed job requirements are required before embedding.")
        return self._status(
            owner_type=EmbeddingOwnerType.JOB.value,
            owner_id=job.id,
            text=build_job_text(job, requirement),
        )

    def embed_candidate_profile(
        self, *, user: User, candidate_id: uuid.UUID, force: bool = False
    ) -> EmbeddingStatus:
        self.authz.require_candidate_owner(user, candidate_id)
        profile = self.repo.latest_confirmed_profile(candidate_id)
        if profile is None:
            raise ConflictError("A confirmed profile is required before embedding.")
        job = self._start_job(
            ProcessingJobType.PROFILE_EMBED.value,
            {"candidate_id": str(candidate_id), "profile_id": str(profile.id)},
        )
        try:
            result = self._persist(
                owner_type=EmbeddingOwnerType.PROFILE.value,
                owner_id=profile.id,
                text=build_profile_text(profile),
                force=force,
            )
            payload = profile.extracted_payload or {}
            for item in profile.experience_items:
                self._persist(
                    owner_type=EmbeddingOwnerType.EXPERIENCE.value,
                    owner_id=item.id,
                    text=build_experience_text(item, payload=payload),
                    force=force,
                    job_type=ProcessingJobType.EXPERIENCE_EMBED.value,
                )
            for item in profile.project_items:
                self._persist(
                    owner_type=EmbeddingOwnerType.PROJECT.value,
                    owner_id=item.id,
                    text=build_project_text(item, payload=payload),
                    force=force,
                    job_type=ProcessingJobType.PROJECT_EMBED.value,
                )
            if profile.source_revision_id:
                revision = self.repo.get_revision(profile.source_revision_id)
                resume = self.repo.get_resume(revision.resume_id) if revision is not None else None
                if revision is not None and resume is not None:
                    for chunk_type, chunk_text in chunks_from_payload(revision.extraction_payload):
                        self._persist(
                            owner_type=EmbeddingOwnerType.RESUME_CHUNK.value,
                            owner_id=resume.id,
                            text=chunk_text,
                            force=force,
                            chunk_type=chunk_type,
                            job_type=ProcessingJobType.RESUME_EMBED.value,
                        )
            self._finish_job(job, ok=True)
            result.processing_job_id = job.id
            audit.record_audit(
                self.db,
                action="profile_embedded",
                resource_type="candidate_profile",
                actor_user_id=user.id,
                resource_id=profile.id,
                metadata={"status": result.status, "model_version": result.model_version},
            )
            return result
        except Exception:
            self._finish_job(job, ok=False, error="embed_failed")
            raise

    def embed_job(self, *, user: User, job_id: uuid.UUID, force: bool = False) -> EmbeddingStatus:
        self.authz.require_job_org_access(user, job_id)
        job = self.repo.get_job(job_id)
        if job is None:
            raise NotFoundError("Job not found.")
        requirement = _latest_confirmed_requirement(job)
        if requirement is None:
            raise ConflictError("Confirmed job requirements are required before embedding.")
        processing = self._start_job(
            ProcessingJobType.JOB_EMBED.value,
            {"job_id": str(job.id), "requirement_id": str(requirement.id)},
        )
        try:
            result = self._persist(
                owner_type=EmbeddingOwnerType.JOB.value,
                owner_id=job.id,
                text=build_job_text(job, requirement),
                force=force,
            )
            self._persist(
                owner_type=EmbeddingOwnerType.JOB_REQUIREMENT.value,
                owner_id=requirement.id,
                text=build_job_requirement_text(job, requirement),
                force=force,
            )
            payload = {
                "normalized_text": job.description_raw,
                "sections": (requirement.extracted_payload or {}).get("sections"),
            }
            for chunk_type, chunk_text in chunks_from_payload(payload):
                label = "description" if chunk_type == CHUNK_FULL else f"description:{chunk_type}"
                self._persist(
                    owner_type=EmbeddingOwnerType.JOB.value,
                    owner_id=job.id,
                    text=chunk_text,
                    force=force,
                    chunk_type=label,
                )
            self._finish_job(processing, ok=True)
            result.processing_job_id = processing.id
            audit.record_audit(
                self.db,
                action="job_embedded",
                resource_type="job",
                actor_user_id=user.id,
                resource_id=job.id,
                metadata={"status": result.status, "model_version": result.model_version},
            )
            return result
        except Exception:
            self._finish_job(processing, ok=False, error="embed_failed")
            raise

    def embed_experience(self, experience_id: uuid.UUID, *, force: bool = False) -> EmbeddingStatus:
        item = self.repo.get_experience(experience_id)
        if item is None:
            raise NotFoundError("Experience not found.")
        profile = self.repo.get_profile(item.candidate_profile_id)
        if profile is None or profile.confirmation_status != ConfirmationStatus.CONFIRMED.value:
            raise ConflictError("Experience embeddings require a confirmed profile.")
        return self._persist(
            owner_type=EmbeddingOwnerType.EXPERIENCE.value,
            owner_id=item.id,
            text=build_experience_text(item, payload=profile.extracted_payload or {}),
            force=force,
            job_type=ProcessingJobType.EXPERIENCE_EMBED.value,
        )

    def embed_project(self, project_id: uuid.UUID, *, force: bool = False) -> EmbeddingStatus:
        item = self.repo.get_project(project_id)
        if item is None:
            raise NotFoundError("Project not found.")
        profile = self.repo.get_profile(item.candidate_profile_id)
        if profile is None or profile.confirmation_status != ConfirmationStatus.CONFIRMED.value:
            raise ConflictError("Project embeddings require a confirmed profile.")
        return self._persist(
            owner_type=EmbeddingOwnerType.PROJECT.value,
            owner_id=item.id,
            text=build_project_text(item, payload=profile.extracted_payload or {}),
            force=force,
            job_type=ProcessingJobType.PROJECT_EMBED.value,
        )

    def similarity(self, *, user: User, payload: SimilarityRequest) -> SimilarityResponse:
        if user.role != UserRole.ADMIN.value:
            raise ForbiddenError("Similarity diagnostics are admin-only.")
        left = self._resolve_row(
            payload.left_embedding_id,
            payload.left_owner_type,
            payload.left_owner_id,
            payload.left_chunk_type,
        )
        right = self._resolve_row(
            payload.right_embedding_id,
            payload.right_owner_type,
            payload.right_owner_id,
            payload.right_chunk_type,
        )
        require_compatible(identity_from_row(left), identity_from_row(right))
        left_vector = list(left.vector)
        right_vector = list(right.vector)
        require_dimension(left_vector, left.dimensions)
        require_dimension(right_vector, right.dimensions)
        require_dimension(left_vector, right.dimensions)
        score = cosine_similarity(left_vector, right_vector)
        return SimilarityResponse(
            similarity=score,
            model_name=left.model_name,
            model_version=left.model_version,
            dimensions=left.dimensions,
            embedding_text_version=left.embedding_text_version,
        )

    def similar_owners(
        self, *, query: list[float], owner_type: str, limit: int = 10
    ) -> list[tuple[Embedding, float]]:
        identity = self.encoder_identity()
        require_dimension(query, identity.dimensions)
        hits = self.repo.similar(query=query, identity=identity, owner_type=owner_type, limit=limit)
        checked: list[tuple[Embedding, float]] = []
        for row, score in hits:
            require_dimension(list(row.vector), identity.dimensions)
            require_dimension(list(row.vector), row.dimensions)
            checked.append((row, score))
        return checked

    def encode_text(self, text: str) -> list[float]:
        started = time.perf_counter()
        vector = self.encoder.encode(text)
        require_dimension(vector, self.encoder.dimensions)
        logger.info(
            "embed_text_done dim=%s elapsed_ms=%s",
            self.encoder.dimensions,
            int((time.perf_counter() - started) * 1000),
        )
        return vector

    def _persist(
        self,
        *,
        owner_type: str,
        owner_id: uuid.UUID,
        text: str,
        force: bool,
        chunk_type: str = CHUNK_FULL,
        job_type: str | None = None,
    ) -> EmbeddingStatus:
        identity = self.encoder_identity()
        digest = content_hash(text)
        existing = self.repo.get_embedding(
            owner_type=owner_type, owner_id=owner_id, chunk_type=chunk_type, identity=identity
        )
        status = classify_status(row=existing, current=identity, content_hash=digest)
        if existing is not None and status == "current" and not force:
            require_dimension(list(existing.vector), identity.dimensions)
            return _to_status(existing, status="current", reused=True)
        processing = None
        if job_type:
            processing = self._start_job(job_type, {"owner_type": owner_type, "owner_id": str(owner_id)})
        try:
            vector = self.encode_text(text)
            require_dimension(vector, identity.dimensions)
            if existing is None:
                existing = Embedding(
                    owner_type=owner_type,
                    owner_id=owner_id,
                    chunk_type=chunk_type,
                    model_name=identity.model_name,
                    model_version=identity.model_version,
                    embedding_text_version=identity.embedding_text_version,
                    dimensions=identity.dimensions,
                    content_hash=digest,
                    vector=vector,
                )
                self.repo.upsert(existing)
            else:
                existing.content_hash = digest
                existing.vector = vector
                existing.dimensions = identity.dimensions
                self.db.flush()
            if processing is not None:
                self._finish_job(processing, ok=True)
            job_id = processing.id if processing else None
            return _to_status(existing, status="current", reused=False, processing_job_id=job_id)
        except Exception:
            if processing is not None:
                self._finish_job(processing, ok=False, error="embed_failed")
            raise

    def _status(
        self, *, owner_type: str, owner_id: uuid.UUID, text: str, chunk_type: str = CHUNK_FULL
    ) -> EmbeddingStatus:
        identity = self.encoder_identity()
        digest = content_hash(text)
        row = self.repo.get_embedding(
            owner_type=owner_type, owner_id=owner_id, chunk_type=chunk_type, identity=identity
        )
        if row is None:
            row = self.repo.latest_owner_embedding(owner_type, owner_id, chunk_type)
        status = classify_status(row=row, current=identity, content_hash=digest)
        if row is None:
            return EmbeddingStatus(
                status="missing",
                owner_type=owner_type,
                owner_id=owner_id,
                chunk_type=chunk_type,
            )
        return _to_status(row, status=status, reused=status == "current")

    def _resolve_row(
        self,
        embedding_id: uuid.UUID | None,
        owner_type: str | None,
        owner_id: uuid.UUID | None,
        chunk_type: str,
    ) -> Embedding:
        if embedding_id is not None:
            row = self.repo.get_embedding_by_id(embedding_id)
        elif owner_type and owner_id:
            row = self.repo.get_embedding(
                owner_type=owner_type,
                owner_id=owner_id,
                chunk_type=chunk_type,
                identity=self.encoder_identity(),
            )
        else:
            raise ConflictError("Provide embedding ids or owner ids.")
        if row is None:
            raise NotFoundError("Embedding not found.")
        return row

    def _start_job(self, job_type: str, payload: dict) -> ProcessingJob:
        job = ProcessingJob(
            type=job_type,
            status=ProcessingJobStatus.PROCESSING.value,
            payload=payload,
            started_at=utcnow(),
        )
        return self.repo.add_job(job)

    def _finish_job(self, job: ProcessingJob, *, ok: bool, error: str | None = None) -> None:
        job.finished_at = utcnow()
        job.status = ProcessingJobStatus.COMPLETED.value if ok else ProcessingJobStatus.FAILED.value
        job.error = error


def _latest_confirmed_requirement(job: Job):
    confirmed = [
        row
        for row in job.requirements
        if row.confirmation_status == ConfirmationStatus.CONFIRMED.value
    ]
    if not confirmed:
        return None
    return max(confirmed, key=lambda row: row.created_at)


def _to_status(
    row: Embedding, *, status: str, reused: bool, processing_job_id: uuid.UUID | None = None
) -> EmbeddingStatus:
    return EmbeddingStatus(
        status=status,  # type: ignore[arg-type]
        owner_type=row.owner_type,
        owner_id=row.owner_id,
        chunk_type=row.chunk_type,
        model_name=row.model_name,
        model_version=row.model_version,
        dimensions=row.dimensions,
        embedding_text_version=row.embedding_text_version,
        content_hash=row.content_hash,
        created_at=row.created_at,
        reused=reused,
        processing_job_id=processing_job_id,
    )
