"""Model artifact I/O. Never commit binaries."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xgboost import XGBClassifier

METADATA_NAME = "metadata.json"
MODEL_NAME = "model.json"


def artifact_dir(root: Path, version: str) -> Path:
    return root / version


def save_artifact(
    *,
    root: Path,
    version: str,
    model: XGBClassifier,
    metadata: dict[str, Any],
) -> Path:
    path = artifact_dir(root, version)
    path.mkdir(parents=True, exist_ok=True)
    model.get_booster().save_model(str(path / MODEL_NAME))
    payload = dict(metadata)
    payload["saved_at"] = datetime.now(timezone.utc).isoformat()
    (path / METADATA_NAME).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def load_artifact(path: Path) -> tuple[XGBClassifier, dict[str, Any]]:
    metadata = json.loads((path / METADATA_NAME).read_text(encoding="utf-8"))
    model = XGBClassifier()
    model.load_model(str(path / MODEL_NAME))
    return model, metadata
