"""Lookup normalization that preserves technical tokens. Not skill equivalence."""

from __future__ import annotations

import re
import unicodedata

# Keep these surfaces intact; hyphens/dots/slashes are meaningful.
PROTECTED_TOKENS = (
    "scikit-learn",
    "node.js",
    "next.js",
    "ci/cd",
    "c++",
    "c#",
    ".net",
)

_PLACEHOLDER = "\x00p{index}\x00"


def normalize_lookup(text: str) -> str:
    """Deterministic lookup key. Does not map ML to Machine Learning."""
    value = unicodedata.normalize("NFKC", text or "").strip()
    value = re.sub(r"[^\S\n]+", " ", value)
    lowered = value.casefold()
    placeholders: dict[str, str] = {}
    for index, token in enumerate(sorted(PROTECTED_TOKENS, key=len, reverse=True)):
        marker = _PLACEHOLDER.format(index=index)
        if token in lowered:
            lowered = lowered.replace(token, marker)
            placeholders[marker] = token
    lowered = re.sub(r"[.,;:]+$", "", lowered)
    lowered = lowered.replace("_", " ").replace("-", " ")
    lowered = re.sub(r"\s+", " ", lowered).strip()
    for marker, token in placeholders.items():
        lowered = lowered.replace(marker, token)
    return lowered


def slugify(name: str) -> str:
    lookup = normalize_lookup(name)
    slug = re.sub(r"[^a-z0-9]+", "-", lookup)
    slug = slug.strip("-")
    for token, repl in (("c++", "cpp"), ("c#", "csharp"), (".net", "dotnet"), ("ci/cd", "ci-cd")):
        slug = slug.replace(token, repl)
    slug = slug.replace(".", "-")
    return slug or "skill"
