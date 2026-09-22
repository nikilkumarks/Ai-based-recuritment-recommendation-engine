"""Reference baselines. Not trained models."""

from __future__ import annotations

import numpy as np

from app.modules.features.schema import ordered_feature_names

FEATURE_INDEX = {name: idx for idx, name in enumerate(ordered_feature_names())}


def random_scores(n: int, seed: int, prior: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(n) * 0.0 + rng.binomial(1, prior, size=n).astype(float) * 0.0 + rng.random(n)


def random_probabilities(n: int, seed: int, prior: float) -> np.ndarray:
    """Reproducible random ranking scores. Prior is recorded but scores are uniform[0,1]."""
    rng = np.random.default_rng(seed)
    _ = prior
    return rng.random(n)


def column_scores(X: np.ndarray, name: str) -> np.ndarray:
    idx = FEATURE_INDEX[name]
    return np.asarray(X[:, idx], dtype=float)
