"""Evaluation metrics. Return unavailable rather than inventing values."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

K_VALUES = (1, 3, 5, 10)
UNAVAILABLE = {"value": None, "reason": "insufficient_data"}


def _binary_metrics(y_true: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    if len(y_true) == 0 or len(set(y_true.tolist())) < 2:
        return {
            "roc_auc": dict(UNAVAILABLE),
            "pr_auc": dict(UNAVAILABLE),
            "precision": dict(UNAVAILABLE),
            "recall": dict(UNAVAILABLE),
            "f1": dict(UNAVAILABLE),
        }
    preds = (scores >= 0.5).astype(int)
    return {
        "roc_auc": {"value": float(roc_auc_score(y_true, scores)), "reason": None},
        "pr_auc": {"value": float(average_precision_score(y_true, scores)), "reason": None},
        "precision": {"value": float(precision_score(y_true, preds, zero_division=0)), "reason": None},
        "recall": {"value": float(recall_score(y_true, preds, zero_division=0)), "reason": None},
        "f1": {"value": float(f1_score(y_true, preds, zero_division=0)), "reason": None},
    }


def _ndcg_at_k(labels: np.ndarray, scores: np.ndarray, k: int) -> float | None:
    if labels.size == 0:
        return None
    order = np.argsort(-scores)
    top = labels[order][:k]
    gains = np.power(2.0, top) - 1.0
    discounts = np.log2(np.arange(2, top.size + 2))
    dcg = float(np.sum(gains / discounts))
    ideal = np.sort(labels)[::-1][:k]
    ideal_gains = np.power(2.0, ideal) - 1.0
    ideal_disc = np.log2(np.arange(2, ideal.size + 2))
    idcg = float(np.sum(ideal_gains / ideal_disc))
    if idcg <= 0:
        return None
    return dcg / idcg


def _ranking_for_groups(
    y_true: np.ndarray, scores: np.ndarray, groups: list[str]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k in K_VALUES:
        precisions: list[float] = []
        recalls: list[float] = []
        ndcgs: list[float] = []
        for job in set(groups):
            mask = np.array([item == job for item in groups])
            labels = y_true[mask]
            ranked = scores[mask]
            if labels.size == 0:
                continue
            order = np.argsort(-ranked)
            top = labels[order][:k]
            precisions.append(float(np.mean(top)) if top.size else 0.0)
            total_pos = float(np.sum(labels))
            if total_pos > 0:
                recalls.append(float(np.sum(top) / total_pos))
            ndcg = _ndcg_at_k(labels, ranked, k)
            if ndcg is not None:
                ndcgs.append(ndcg)
        result[f"precision_at_{k}"] = (
            {"value": float(np.mean(precisions)), "reason": None}
            if precisions
            else dict(UNAVAILABLE)
        )
        result[f"recall_at_{k}"] = (
            {"value": float(np.mean(recalls)), "reason": None} if recalls else dict(UNAVAILABLE)
        )
        result[f"ndcg_at_{k}"] = (
            {"value": float(np.mean(ndcgs)), "reason": None} if ndcgs else dict(UNAVAILABLE)
        )
    return result


def evaluate_scores(
    y_true: list[int] | np.ndarray,
    scores: list[float] | np.ndarray,
    groups: list[str],
) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=float)
    s = np.asarray(scores, dtype=float)
    metrics = _binary_metrics(y, s)
    metrics.update(_ranking_for_groups(y, s, groups))
    return metrics


def metric_value(metrics: dict[str, Any], name: str) -> float | None:
    payload = metrics.get(name)
    if not isinstance(payload, dict):
        return None
    value = payload.get("value")
    return float(value) if isinstance(value, (int, float)) else None
