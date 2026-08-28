"""Resume upload and document-processing constants. Parser version lives here only."""

from __future__ import annotations

from app.core.config import get_settings

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
OCTET_STREAM = "application/octet-stream"

ALLOWED_RESUME_MIMES = frozenset({PDF_MIME, DOCX_MIME})
PDF_MAGIC = b"%PDF"
ZIP_MAGIC = b"PK\x03\x04"

STORAGE_PREFIX = "resumes"
STORAGE_KEY_PATTERN = r"^resumes/[a-f0-9]{64}$"

OCR_NOT_ENABLED = "Document appears to require OCR; OCR is not currently enabled."
MIN_USABLE_TEXT_CHARS = 40


def parser_version() -> str:
    return get_settings().document_parser_version
