from __future__ import annotations

from app.modules.documents.constants import OCR_NOT_ENABLED, parser_version
from app.modules.documents.processor import extract_document, normalize_text
from tests.fixtures.resume_docs import (
    blank_pdf,
    encrypted_pdf,
    heading_docx,
    malformed_docx,
    malformed_pdf,
    normal_docx,
    normal_pdf,
    pdf_containing,
    sectioned_pdf,
)


def test_normalize_preserves_technical_tokens() -> None:
    raw = "Used  C++  and   Node.js\nNext.js   CI/CD   scikit-learn   Machine   Learning"
    out = normalize_text(raw)
    assert "C++" in out
    assert "Node.js" in out
    assert "Next.js" in out
    assert "CI/CD" in out
    assert "scikit-learn" in out
    assert "Machine Learning" in out


def test_valid_pdf_extracts_text() -> None:
    result = extract_document(kind="pdf", data=normal_pdf())
    assert result.status == "ready"
    assert "Ada Lovelace" in result.payload["normalized_text"]
    assert result.payload["parser_version"] == parser_version()


def test_sectioned_pdf_detects_conservative_headings() -> None:
    result = extract_document(kind="pdf", data=sectioned_pdf())
    assert result.status == "ready"
    sections = result.payload.get("sections") or {}
    assert "experience" in sections
    assert "education" in sections


def test_pdf_terms_survive_extraction() -> None:
    for term in ["C++", "Node.js", "Next.js", "CI/CD", "ML", "Machine Learning"]:
        result = extract_document(kind="pdf", data=pdf_containing(term))
        assert result.status == "ready", term
        assert term in result.payload["normalized_text"], term


def test_valid_docx_extracts_text() -> None:
    result = extract_document(kind="docx", data=normal_docx())
    assert result.status == "ready"
    assert "Ada Lovelace" in result.payload["normalized_text"]


def test_docx_headings_and_tables_survive() -> None:
    result = extract_document(kind="docx", data=heading_docx())
    assert result.status == "ready"
    text = result.payload["normalized_text"]
    assert "Example Corp" in text
    assert "Python" in text


def test_malformed_pdf_fails_safely() -> None:
    result = extract_document(kind="pdf", data=malformed_pdf())
    assert result.status == "failed"
    assert result.error


def test_malformed_docx_fails_safely() -> None:
    result = extract_document(kind="docx", data=malformed_docx())
    assert result.status == "failed"


def test_blank_pdf_needs_ocr() -> None:
    result = extract_document(kind="pdf", data=blank_pdf())
    assert result.status == "needs_ocr"
    assert result.error == OCR_NOT_ENABLED


def test_encrypted_pdf_fails_safely() -> None:
    result = extract_document(kind="pdf", data=encrypted_pdf())
    assert result.status == "failed"
    assert "encrypt" in (result.error or "").lower()
