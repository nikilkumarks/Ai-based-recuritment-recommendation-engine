"""Upload validation: size, MIME, magic bytes, empty files, unsafe names."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.errors import InvalidDocumentError, PayloadTooLargeError, UnsupportedMediaError
from app.modules.documents.constants import ALLOWED_RESUME_MIMES, DOCX_MIME, OCTET_STREAM, PDF_MIME
from app.modules.documents.mime import sniff_kind


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    mime_type: str
    kind: str
    data: bytes


def safe_filename(raw: str | None) -> str:
    name = (raw or "resume").strip() or "resume"
    if "\x00" in name:
        raise InvalidDocumentError("Filename is not allowed.")
    normalized = name.replace("\\", "/")
    if ".." in normalized.split("/") or normalized.startswith("/") or "/" in normalized:
        raise InvalidDocumentError("Filename is not allowed.")
    return name[:512]


def validate_upload(*, filename: str | None, declared_mime: str | None, data: bytes) -> ValidatedUpload:
    settings = get_settings()
    if not data:
        raise InvalidDocumentError("Empty files are not accepted.")
    if len(data) > settings.max_resume_bytes:
        raise PayloadTooLargeError(
            f"File exceeds the maximum size of {settings.max_resume_bytes} bytes."
        )
    safe_name = safe_filename(filename)
    declared = (declared_mime or "").split(";")[0].strip().lower()
    if declared and declared not in {OCTET_STREAM, ""} and declared not in ALLOWED_RESUME_MIMES:
        raise UnsupportedMediaError("Only PDF and DOCX resumes are accepted.")

    kind = sniff_kind(data)
    if kind is None:
        raise InvalidDocumentError("File signature is not a supported PDF or DOCX document.")

    expected_mime = PDF_MIME if kind == "pdf" else DOCX_MIME
    if declared in ALLOWED_RESUME_MIMES and declared != expected_mime:
        raise InvalidDocumentError("Declared file type does not match the file contents.")
    return ValidatedUpload(filename=safe_name, mime_type=expected_mime, kind=kind, data=data)
