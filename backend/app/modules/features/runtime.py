"""Process-cached trained-model scoring with baseline fallback.

Matching may import this module. Do not import app.modules.ml (HTTP-free serving
lives here so recruitment requests survive missing or incompatible artifacts).
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from xgboost import XGBClassifier

from app.core.config import get_settings
from app.models import MlModel
from app.models.enums import MlModelStatus
from app.modules.features.explain import explain_vector
from app.modules.features.schema import (
    ML_FEATURE_SCHEMA_VERSION,
    ML_PREPROCESS_VERSION,
    ordered_feature_names,
    vectorize_features,
)
from app.modules.matching.constants import SCORING_MODE_BASELINE, SCORING_MODE_TRAINED

_CACHE_LOCK = threading.Lock()
_CACHED_VERSION: str | None = None
_CACHED_MODEL: XGBClassifier | None = None
_CACHED_METADATA: dict[str, Any] | None = None


@dataclass(frozen=True)
class InferenceResult:
    scoring_mode: str
    model_version: str | None
    model_relevance_score: float | None
    ml_explanations: list[dict[str, Any]]
    fallback_reason: str | None

    @property
    def trained(self) -> bool:
        return self.scoring_mode == SCORING_MODE_TRAINED and self.model_relevance_score is not None


def reset_model_cache() -> None:
    global _CACHED_VERSION, _CACHED_MODEL, _CACHED_METADATA
    with _CACHE_LOCK:
        _CACHED_VERSION = None
        _CACHED_MODEL = None
        _CACHED_METADATA = None


def artifact_root() -> Path:
    settings = get_settings()
    path = Path(settings.model_artifact_dir)
    if path.is_absolute():
        return path
    repo = Path(__file__).resolve().parents[4]
    return (repo / path).resolve()


def score_features(
    db: Session,
    features: dict[str, Any],
    *,
    ontology_version: str | None = None,
    embedding_identity: str | None = None,
) -> InferenceResult:
    """Score one pair. Never raises for model failures; falls back to baseline."""
    try:
        active = db.scalar(select(MlModel).where(MlModel.status == MlModelStatus.ACTIVE.value))
    except Exception:
        return _baseline("model_lookup_failed")
    if active is None:
        reset_model_cache()
        return _baseline(None)
    loaded = _load_active(active)
    if isinstance(loaded, str):
        return _baseline(loaded)
    model, metadata = loaded
    expected_schema = metadata.get("feature_schema_version")
    if expected_schema and expected_schema != ML_FEATURE_SCHEMA_VERSION:
        return _baseline("feature_schema_mismatch")
    preprocess = metadata.get("preprocessing_version")
    if preprocess and preprocess != ML_PREPROCESS_VERSION:
        return _baseline("preprocessing_version_mismatch")
    expected_names = list(metadata.get("feature_names") or ordered_feature_names())
    if expected_names != ordered_feature_names():
        return _baseline("feature_schema_mismatch")
    if not _metadata_compatible(metadata, ontology_version, embedding_identity):
        return _baseline("incompatible_ontology_or_embedding_metadata")
    vector, error = vectorize_features(features)
    if error or not vector:
        return _baseline(error or "incompatible_feature_vector")
    if len(vector) != len(expected_names):
        return _baseline("incompatible_feature_vector")
    try:
        probability = float(model.predict_proba([vector])[0, 1])
    except Exception:
        return _baseline("model_loading_failure")
    explanation = explain_vector(model, vector, expected_names)
    return InferenceResult(
        scoring_mode=SCORING_MODE_TRAINED,
        model_version=active.version,
        model_relevance_score=round(probability, 4),
        ml_explanations=[explanation],
        fallback_reason=None,
    )


def _baseline(reason: str | None) -> InferenceResult:
    return InferenceResult(
        scoring_mode=SCORING_MODE_BASELINE,
        model_version=None,
        model_relevance_score=None,
        ml_explanations=[],
        fallback_reason=reason,
    )


def _load_active(active: MlModel) -> tuple[XGBClassifier, dict[str, Any]] | str:
    global _CACHED_VERSION, _CACHED_MODEL, _CACHED_METADATA
    with _CACHE_LOCK:
        if _CACHED_VERSION == active.version and _CACHED_MODEL is not None and _CACHED_METADATA is not None:
            return _CACHED_MODEL, _CACHED_METADATA
        directory = artifact_root() / (active.artifact_uri or active.version)
        model_path = directory / "model.json"
        meta_path = directory / "metadata.json"
        if not model_path.is_file() or not meta_path.is_file():
            return "missing_artifact"
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            model = XGBClassifier()
            model.load_model(str(model_path))
        except Exception:
            return "corrupt_artifact"
        _CACHED_VERSION = active.version
        _CACHED_MODEL = model
        _CACHED_METADATA = metadata
        return model, metadata


def _metadata_compatible(
    metadata: dict[str, Any],
    ontology_version: str | None,
    embedding_identity: str | None,
) -> bool:
    trained_ontologies = set(metadata.get("ontology_versions") or [])
    if ontology_version and trained_ontologies and ontology_version not in trained_ontologies:
        return False
    trained_embeddings = set(metadata.get("embedding_identity") or [])
    if embedding_identity and trained_embeddings and embedding_identity not in trained_embeddings:
        return False
    return True
