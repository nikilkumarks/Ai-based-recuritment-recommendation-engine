"""HTTP routes for resume upload, listing, detail, and deletion."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.documents.schemas import MessageResponse, ResumeListResponse, ResumeSummary
from app.modules.documents.service import DocumentService
from app.modules.documents.storage import BlobStore, get_blob_store
from app.modules.documents.validators import validate_upload
from app.modules.identity.dependencies import get_current_active_user

router = APIRouter(tags=["resumes"])


def get_document_service(
    db: Session = Depends(get_db),
    blobs: BlobStore = Depends(get_blob_store),
) -> DocumentService:
    return DocumentService(db, blobs)


@router.post(
    "/candidates/{candidate_id}/resumes",
    response_model=ResumeSummary,
    status_code=201,
)
async def upload_resume(
    candidate_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> ResumeSummary:
    data = await file.read()
    upload = validate_upload(filename=file.filename, declared_mime=file.content_type, data=data)
    return service.upload(user=user, candidate_id=candidate_id, upload=upload)


@router.get("/candidates/{candidate_id}/resumes", response_model=ResumeListResponse)
def list_resumes(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> ResumeListResponse:
    return ResumeListResponse(items=service.list_resumes(user=user, candidate_id=candidate_id))


@router.get("/candidates/{candidate_id}/resumes/{resume_id}", response_model=ResumeSummary)
def get_resume(
    candidate_id: uuid.UUID,
    resume_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> ResumeSummary:
    return service.get_resume(user=user, candidate_id=candidate_id, resume_id=resume_id)


@router.delete("/candidates/{candidate_id}/resumes/{resume_id}", response_model=MessageResponse)
def delete_resume(
    candidate_id: uuid.UUID,
    resume_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> MessageResponse:
    service.delete_resume(user=user, candidate_id=candidate_id, resume_id=resume_id)
    return MessageResponse(message="Resume deleted.")
