"""Light text preprocessing for NLP. Does not rewrite or generate content."""

from __future__ import annotations

import re

from app.modules.documents.processor import normalize_text


def preprocess_document_text(raw: str) -> str:
    text = normalize_text(raw)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def snippet(text: str, start: int, end: int, *, radius: int = 40) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    return text[lo:hi]


def line_blocks(section: str) -> list[str]:
    parts = re.split(r"\n\s*\n", section.strip())
    return [part.strip() for part in parts if part.strip()]
