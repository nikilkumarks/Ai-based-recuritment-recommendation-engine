"""Embeddings constants. Not match scores."""

from __future__ import annotations

CHUNK_FULL = "full"
TEXT_VERSION_V1 = "embedding-text-v1"
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Application pin for the encoder identity. Not a Hugging Face git SHA.
DEFAULT_MODEL_VERSION = "all-minilm-l6-v2-v1"
HASHING_BACKEND = "hashing"
HASHING_MODEL_NAME = "hashing-encoder"
HASHING_MODEL_VERSION = "hashing-v1"
HASHING_DIMENSIONS = 8
SENTENCE_TRANSFORMERS_BACKEND = "sentence_transformers"
CHUNK_CHAR_LIMIT = 1800
IDENTICAL_COSINE_TOLERANCE = 1e-6
STABLE_COSINE_TOLERANCE = 1e-5
