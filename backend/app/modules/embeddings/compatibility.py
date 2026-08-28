"""Encoder/model/text-version compatibility. Stale vectors are not compared silently."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import IncompatibleEmbeddingError
from app.models import Embedding


@dataclass(frozen=True)
class EncoderIdentity:
    model_name: str
    model_version: str
    dimensions: int
    embedding_text_version: str


def identity_from_row(row: Embedding) -> EncoderIdentity:
    return EncoderIdentity(
        model_name=row.model_name,
        model_version=row.model_version,
        dimensions=row.dimensions,
        embedding_text_version=row.embedding_text_version,
    )


def compatible(left: EncoderIdentity, right: EncoderIdentity) -> bool:
    return (
        left.model_name == right.model_name
        and left.model_version == right.model_version
        and left.dimensions == right.dimensions
        and left.embedding_text_version == right.embedding_text_version
    )


def require_compatible(left: EncoderIdentity, right: EncoderIdentity) -> None:
    if not compatible(left, right):
        raise IncompatibleEmbeddingError(
            "Embeddings cannot be compared across model, version, dimension, or text version."
        )


def classify_status(
    *,
    row: Embedding | None,
    current: EncoderIdentity,
    content_hash: str,
) -> str:
    if row is None:
        return "missing"
    stored = identity_from_row(row)
    stored_len = len(list(row.vector)) if row.vector is not None else 0
    if (
        stored.model_name != current.model_name
        or stored.model_version != current.model_version
        or stored.dimensions != current.dimensions
        or stored_len != current.dimensions
        or stored_len != stored.dimensions
    ):
        return "incompatible"
    if stored.embedding_text_version != current.embedding_text_version or row.content_hash != content_hash:
        return "stale"
    return "current"
