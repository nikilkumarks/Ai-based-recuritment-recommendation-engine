"""DTOs for resume upload and document processing. Not SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Resume
from app.modules.documents.constants import parser_version


class ResumeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime_type: str
    file_size: int
    parse_status: str
    parser_version: str | None = None
    created_at: datetime
    parsed_at: datetime | None = None
    duplicate: bool = False


class ResumeListResponse(BaseModel):
    items: list[ResumeSummary]


class MessageResponse(BaseModel):
    message: str


def resume_to_summary(
    resume: Resume,
    *,
    duplicate: bool = False,
    latest_parser_version: str | None = None,
) -> ResumeSummary:
    version = latest_parser_version
    if version is None and resume.parse_status in {"ready", "needs_ocr"}:
        version = parser_version()
    return ResumeSummary(
        id=resume.id,
        filename=resume.original_filename,
        mime_type=resume.mime_type,
        file_size=resume.file_size,
        parse_status=resume.parse_status,
        parser_version=version,
        created_at=resume.created_at,
        parsed_at=resume.parsed_at,
        duplicate=duplicate,
    )
