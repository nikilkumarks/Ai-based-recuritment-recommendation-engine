"""Recruiter decision DTOs. Notes are recruiter-private."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DecisionAction = Literal["shortlist", "reject", "review"]
ReasonCode = Literal[
    "skill_gap",
    "experience_gap",
    "education_mismatch",
    "strong_skill_match",
    "strong_project_evidence",
    "insufficient_evidence",
    "other",
]


class RecruiterDecisionCreate(BaseModel):
    action: DecisionAction
    reason: ReasonCode | None = None
    note: str | None = Field(default=None, max_length=2000)


class RecruiterDecisionView(BaseModel):
    id: uuid.UUID
    recruiter_id: uuid.UUID
    organization_id: uuid.UUID | None = None
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    action: str
    reason: str | None = None
    note: str | None = None
    match_run_id: uuid.UUID | None = None
    feature_snapshot_id: uuid.UUID | None = None
    created_at: datetime


class RecruiterDecisionListResponse(BaseModel):
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    current_action: str | None = None
    items: list[RecruiterDecisionView]
    append_only: bool = True
    label_note: str = (
        "Recruiter decisions are behavioral labels reflecting recruiter actions, "
        "not ground-truth hiring outcomes."
    )
