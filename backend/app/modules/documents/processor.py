"""PDF/DOCX text extraction and conservative heading detection. Not NLP or skill extraction."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any

from app.modules.documents.constants import MIN_USABLE_TEXT_CHARS, OCR_NOT_ENABLED, parser_version

_HEADING_MAP: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("summary", re.compile(r"^(professional\s+)?summary$|^profile$|^about\s+me$|^(career\s+)?objective$", re.I)),
    ("experience", re.compile(r"^(work\s+|professional\s+|internship\s+|employment\s+|relevant\s+)?experience$|^(employment|work)\s+history$|^internships$", re.I)),
    ("education", re.compile(r"^education(al)?(\s+(qualification|background|record|credentials))?$|^academic\s+(background|record)$|^qualifications$", re.I)),
    ("projects", re.compile(r"^(academic\s+|personal\s+|key\s+|featured\s+|selected\s+|technical\s+)?projects?(\s+experience)?$", re.I)),
    ("skills", re.compile(r"^(technical\s+|core\s+|key\s+)?skills?(\s+&\s+technologies)?$|^technologies(\s+&\s+tools)?$|^technical\s+expertise$", re.I)),
    ("certifications", re.compile(r"^certifications?$|^certificates?$|^licenses?$|^professional\s+certifications?$|^(courses|training)\s+&\s+certifications?$", re.I)),
    ("achievements", re.compile(r"^(key\s+)?achievements$|^honors(\s+&\s+awards)?$|^awards$", re.I)),
)


@dataclass
class ExtractionOutcome:
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def normalize_text(raw: str) -> str:
    """Collapse excess whitespace without damaging tokens such as C++, Node.js, CI/CD."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\S\n]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_sections(text: str) -> dict[str, str] | None:
    """Rule-based headings only."""
    lines = text.split("\n")
    hits: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        key = _heading_key(line)
        if key:
            hits.append((index, key))
    if len(hits) < 1:
        return None
    sections: dict[str, str] = {}
    for i, (start, key) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(lines)
        body = "\n".join(lines[start + 1 : end]).strip()
        if body:
            if key in sections:
                sections[key] = f"{sections[key]}\n\n{body}"
            else:
                sections[key] = body
    return sections or None


def _heading_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) > 60:
        return None
    cleaned = re.sub(r"^(?:[\d\.\-\*•\[\]]+\s*)+", "", stripped)
    cleaned = re.sub(r"[\s:\-\#\=]+$", "", cleaned).strip()
    if not cleaned or len(cleaned) > 48:
        return None
    for key, pattern in _HEADING_MAP:
        if pattern.fullmatch(cleaned):
            return key
    return None


def extract_document(*, kind: str, data: bytes) -> ExtractionOutcome:
    try:
        if kind == "pdf":
            return _extract_pdf(data)
        if kind == "docx":
            return _extract_docx(data)
    except Exception:
        return ExtractionOutcome(status="failed", error="The document could not be read.")
    return ExtractionOutcome(status="failed", error="Unsupported document kind.")


def _extract_pdf(data: bytes) -> ExtractionOutcome:
    from pypdf import PdfReader
    from pypdf.errors import FileNotDecryptedError, PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError:
        return ExtractionOutcome(status="failed", error="The PDF is malformed.")
    except Exception:
        return ExtractionOutcome(status="failed", error="The PDF could not be read.")

    if reader.is_encrypted:
        try:
            decrypted = reader.decrypt("")
            if int(decrypted) == 0:
                return ExtractionOutcome(status="failed", error="The PDF is encrypted.")
        except Exception:
            return ExtractionOutcome(status="failed", error="The PDF is encrypted.")

    pages: list[str] = []
    try:
        for page in reader.pages:
            pages.append(page.extract_text() or "")
    except FileNotDecryptedError:
        return ExtractionOutcome(status="failed", error="The PDF is encrypted.")
    except Exception:
        return ExtractionOutcome(status="failed", error="The PDF could not be read.")

    normalized = normalize_text("\n".join(pages))
    page_count = len(reader.pages)
    if not normalized or len(normalized) < MIN_USABLE_TEXT_CHARS:
        return ExtractionOutcome(
            status="needs_ocr",
            error=OCR_NOT_ENABLED,
            payload={
                "normalized_text": normalized,
                "char_count": len(normalized),
                "page_count": page_count,
                "parser_version": parser_version(),
                "warnings": ["textless_or_scanned_pdf"],
            },
        )
    return _ready_payload(normalized, page_count=page_count)


def _extract_docx(data: bytes) -> ExtractionOutcome:
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError

    try:
        document = Document(io.BytesIO(data))
    except PackageNotFoundError:
        return ExtractionOutcome(status="failed", error="The DOCX is malformed.")
    except Exception:
        return ExtractionOutcome(status="failed", error="The DOCX could not be read.")

    parts: list[str] = []
    for paragraph in document.paragraphs:
        parts.append(paragraph.text)
    for table in document.tables:
        for row in table.rows:
            parts.append(" ".join(cell.text for cell in row.cells))
    normalized = normalize_text("\n".join(parts))
    if not normalized:
        return ExtractionOutcome(status="failed", error="The DOCX did not contain extractable text.")
    return _ready_payload(normalized, page_count=None)


def _ready_payload(normalized: str, *, page_count: int | None) -> ExtractionOutcome:
    sections = detect_sections(normalized)
    payload: dict[str, Any] = {
        "normalized_text": normalized,
        "char_count": len(normalized),
        "page_count": page_count,
        "parser_version": parser_version(),
        "warnings": [],
    }
    if sections:
        payload["sections"] = sections
    return ExtractionOutcome(status="ready", payload=payload)
