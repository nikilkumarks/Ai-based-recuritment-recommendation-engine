"""Suggested skill path DTOs. Not hiring predictions."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class CareerPathListResponse(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID | None = None
    label: str = "Suggested Skill Path"
    disclaimer: str = (
        "Suggested Skill Path uses the ontology graph. It is not a guaranteed career path "
        "and is not a probability of hiring or selection."
    )
    items: list[dict[str, Any]] = Field(default_factory=list)
