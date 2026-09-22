"""Structured model explanations. Never LLM prose. Never fabricate SHAP values."""

from __future__ import annotations

from typing import Any

import numpy as np
from xgboost import XGBClassifier


def explain_vector(model: XGBClassifier, vector: list[float], feature_names: list[str]) -> dict[str, Any]:
    array = np.asarray([vector], dtype=float)
    shap_values = _shap(model, array, feature_names)
    if shap_values is not None:
        return {
            "kind": "ml_model",
            "method": "shap",
            "title": "ML model explanation",
            "note": (
                "The trained model assigned a shortlist relevance score based on these features. "
                "This is not a hiring explanation."
            ),
            "features": shap_values,
        }
    importances = getattr(model, "feature_importances_", None)
    items: list[dict[str, Any]] = []
    if importances is not None:
        for name, weight in zip(feature_names, importances.tolist(), strict=False):
            items.append({"feature": name, "importance": float(weight), "contribution": None})
        items.sort(key=lambda row: row["importance"], reverse=True)
    return {
        "kind": "ml_model",
        "method": "feature_importance",
        "title": "ML model explanation",
        "note": (
            "The trained model assigned a shortlist relevance score based on these features. "
            "SHAP values were unavailable; these are global tree importances, not fabricated SHAP values."
        ),
        "features": items[:12],
    }


def _shap(model: XGBClassifier, array: np.ndarray, feature_names: list[str]) -> list[dict[str, Any]] | None:
    try:
        import shap
    except Exception:
        return None
    try:
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(array)
        if isinstance(values, list):
            values = values[-1]
        row = np.asarray(values)[0]
        items = [
            {"feature": name, "contribution": float(value), "importance": abs(float(value))}
            for name, value in zip(feature_names, row.tolist(), strict=False)
        ]
        items.sort(key=lambda item: item["importance"], reverse=True)
        return items[:12]
    except Exception:
        return None
