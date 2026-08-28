"""Cosine similarity as a reusable semantic feature. Not a recruitment score."""

from __future__ import annotations

from collections.abc import Sequence

from app.core.errors import IncompatibleEmbeddingError
from app.modules.embeddings.constants import IDENTICAL_COSINE_TOLERANCE


def require_dimension(vector: Sequence[float], expected: int) -> None:
    """Refuse mismatched lengths. Never truncate or pad."""
    actual = len(vector)
    if expected <= 0:
        raise IncompatibleEmbeddingError("Expected embedding dimension must be positive.")
    if actual != expected:
        raise IncompatibleEmbeddingError(
            f"Vector dimension {actual} does not match expected dimension {expected}."
        )


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise IncompatibleEmbeddingError("Vector dimensions do not match.")
    if not left:
        raise IncompatibleEmbeddingError("Empty vectors cannot be compared.")
    dot = 0.0
    left_norm_sq = 0.0
    right_norm_sq = 0.0
    for a, b in zip(left, right, strict=True):
        fa = float(a)
        fb = float(b)
        dot += fa * fb
        left_norm_sq += fa * fa
        right_norm_sq += fb * fb
    if left_norm_sq == 0.0 or right_norm_sq == 0.0:
        raise IncompatibleEmbeddingError("Zero vectors cannot be compared.")
    value = dot / ((left_norm_sq**0.5) * (right_norm_sq**0.5))
    if value > 1.0:
        value = 1.0
    elif value < -1.0:
        value = -1.0
    return value


def is_identical_cosine(value: float) -> bool:
    return abs(value - 1.0) <= IDENTICAL_COSINE_TOLERANCE
