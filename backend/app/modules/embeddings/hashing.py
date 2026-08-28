"""SHA-256 of embedding source text. Do not log the text."""

from __future__ import annotations

import hashlib
import re


def normalize_source_text(text: str) -> str:
    """Safe whitespace collapse only. Does not rewrite technical tokens."""
    value = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[^\S\n]+", " ", value)
    lines = [line.strip() for line in value.split("\n")]
    value = "\n".join(line for line in lines if line)
    return value.strip()


def content_hash(text: str) -> str:
    normalized = normalize_source_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
