"""MIME and magic-byte helpers. Filename extensions are never trusted alone."""

from __future__ import annotations

from app.modules.documents.constants import DOCX_MIME, PDF_MAGIC, PDF_MIME, ZIP_MAGIC


def sniff_kind(data: bytes) -> str | None:
    if data.startswith(PDF_MAGIC):
        return "pdf"
    if data.startswith(ZIP_MAGIC) and _looks_like_docx(data):
        return "docx"
    return None


def _looks_like_docx(data: bytes) -> bool:
    """DOCX is a ZIP with word/document.xml. Do not execute macros or embedded objects."""
    try:
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
    except Exception:
        return False
    return "[Content_Types].xml" in names and "word/document.xml" in names


def mime_for_kind(kind: str) -> str:
    if kind == "pdf":
        return PDF_MIME
    if kind == "docx":
        return DOCX_MIME
    raise ValueError(kind)
