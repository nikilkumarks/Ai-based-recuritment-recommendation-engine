"""Process-cached embedding encoder. Loads once; never logs source text."""

from __future__ import annotations

import hashlib
import logging
import math
import time
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import UnprocessableError
from app.modules.embeddings.compatibility import EncoderIdentity
from app.modules.embeddings.constants import (
    DEFAULT_MODEL_NAME,
    HASHING_BACKEND,
    HASHING_DIMENSIONS,
    HASHING_MODEL_NAME,
    HASHING_MODEL_VERSION,
    SENTENCE_TRANSFORMERS_BACKEND,
)
from app.modules.embeddings.similarity import require_dimension

logger = logging.getLogger("prj385.embeddings")

_ENCODER: Encoder | None = None


class Encoder(Protocol):
    model_name: str
    model_version: str
    dimensions: int

    def encode(self, text: str) -> list[float]: ...

    def identity(self, text_version: str) -> EncoderIdentity: ...


class HashingEncoder:
    """Deterministic stand-in for tests. Not a semantic model and not MiniLM."""

    def __init__(
        self,
        *,
        model_name: str = HASHING_MODEL_NAME,
        model_version: str = HASHING_MODEL_VERSION,
        dimensions: int = HASHING_DIMENSIONS,
    ) -> None:
        lowered = model_name.strip().lower()
        if "minilm" in lowered or "sentence-transformers" in lowered:
            raise ValueError("HashingEncoder cannot use a Sentence Transformer model name.")
        if model_name.strip() == DEFAULT_MODEL_NAME:
            raise ValueError("HashingEncoder cannot use the production MiniLM model name.")
        self.model_name = model_name
        self.model_version = model_version
        self.dimensions = dimensions

    def encode(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        needed = self.dimensions
        block = digest
        while len(values) < needed:
            for index in range(0, len(block), 4):
                raw = int.from_bytes(block[index : index + 4], "big")
                values.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
                if len(values) >= needed:
                    break
            block = hashlib.sha256(block).digest()
        vector = _l2_normalize(values[:needed])
        require_dimension(vector, self.dimensions)
        return vector

    def identity(self, text_version: str) -> EncoderIdentity:
        return EncoderIdentity(
            model_name=self.model_name,
            model_version=self.model_version,
            dimensions=self.dimensions,
            embedding_text_version=text_version,
        )


class SentenceTransformerEncoder:
    def __init__(self, *, model_name: str, model_version: str, model_revision: str = "") -> None:
        started = time.perf_counter()
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model_version = model_version
        self.model_revision = (model_revision or "").strip()
        kwargs: dict[str, str] = {}
        if self.model_revision:
            kwargs["revision"] = self.model_revision
        self._model = SentenceTransformer(model_name, **kwargs)
        dim = self._model.get_sentence_embedding_dimension()
        if not dim:
            raise UnprocessableError("The embedding encoder did not report a dimension.")
        self.dimensions = int(dim)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "encoder_loaded model=%s app_version=%s revision=%s dim=%s elapsed_ms=%s",
            model_name,
            model_version,
            self.model_revision or "library-default",
            self.dimensions,
            elapsed_ms,
        )

    def encode(self, text: str) -> list[float]:
        started = time.perf_counter()
        vector = self._model.encode(text, normalize_embeddings=False, show_progress_bar=False)
        values = [float(item) for item in vector.tolist()]
        require_dimension(values, self.dimensions)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info("encode_done model=%s dim=%s elapsed_ms=%s", self.model_name, self.dimensions, elapsed_ms)
        return values

    def identity(self, text_version: str) -> EncoderIdentity:
        return EncoderIdentity(
            model_name=self.model_name,
            model_version=self.model_version,
            dimensions=self.dimensions,
            embedding_text_version=text_version,
        )


def get_encoder() -> Encoder:
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = _build_encoder()
    return _ENCODER


def reset_encoder() -> None:
    global _ENCODER
    _ENCODER = None


def set_encoder(encoder: Encoder) -> None:
    global _ENCODER
    _ENCODER = encoder


def _build_encoder() -> Encoder:
    settings = get_settings()
    backend = (settings.embedding_backend or SENTENCE_TRANSFORMERS_BACKEND).strip().lower()
    if backend == HASHING_BACKEND:
        return HashingEncoder()
    name = settings.resolved_embedding_model_name()
    if not name:
        raise UnprocessableError("EMBEDDING_MODEL_NAME is not configured.")
    return SentenceTransformerEncoder(
        model_name=name,
        model_version=settings.embedding_model_version,
        model_revision=settings.embedding_model_revision,
    )


def _l2_normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(item * item for item in values))
    if norm == 0:
        return values
    return [item / norm for item in values]
