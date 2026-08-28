"""Section chunks from existing extraction output. Does not re-parse PDFs."""

from __future__ import annotations

from app.modules.embeddings.constants import CHUNK_CHAR_LIMIT, CHUNK_FULL
from app.modules.embeddings.hashing import normalize_source_text

SECTION_ORDER = (
    "summary",
    "experience",
    "projects",
    "skills",
    "education",
    "certifications",
    "required",
    "preferred",
    "full",
)


def chunks_from_payload(payload: dict | None) -> list[tuple[str, str]]:
    """Return (chunk_type, text) pairs from an extraction revision or job payload."""
    data = payload or {}
    sections = data.get("sections") or {}
    found: list[tuple[str, str]] = []
    if isinstance(sections, dict):
        for key in SECTION_ORDER:
            text = normalize_source_text(str(sections.get(key) or ""))
            if text:
                found.extend(_split(key, text))
    if found:
        return found
    body = normalize_source_text(str(data.get("normalized_text") or data.get("description_raw") or ""))
    if not body:
        return []
    return _split(CHUNK_FULL, body)


def _split(chunk_type: str, text: str) -> list[tuple[str, str]]:
    if len(text) <= CHUNK_CHAR_LIMIT:
        return [(chunk_type, text)]
    parts: list[tuple[str, str]] = []
    remaining = text
    index = 1
    while remaining:
        piece = remaining[:CHUNK_CHAR_LIMIT]
        cut = piece.rfind("\n")
        if cut < CHUNK_CHAR_LIMIT // 3:
            cut = piece.rfind(". ")
        if cut >= CHUNK_CHAR_LIMIT // 3:
            piece = remaining[: cut + 1]
        piece = piece.strip()
        if piece:
            if index == 1 and len(remaining) <= CHUNK_CHAR_LIMIT:
                label = chunk_type
            else:
                label = f"{chunk_type}:{index}"
            parts.append((label, piece))
        remaining = remaining[len(piece) :].strip()
        index += 1
    return parts
