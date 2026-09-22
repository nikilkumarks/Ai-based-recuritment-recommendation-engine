"""Read-only dataset snapshot access for the training CLI."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DatasetSnapshot, RecruiterDecision


def load_snapshot(db: Session, snapshot_id: uuid.UUID) -> DatasetSnapshot | None:
    return db.get(DatasetSnapshot, snapshot_id)


def snapshot_rows(snapshot: DatasetSnapshot) -> list[dict[str, Any]]:
    return list(snapshot.rows or [])


def decision_fingerprint(db: Session) -> str:
    rows = db.scalars(select(RecruiterDecision.id).order_by(RecruiterDecision.id.asc())).all()
    return ",".join(str(item) for item in rows)
