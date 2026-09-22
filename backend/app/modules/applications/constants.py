"""Recruiter decision constants. Behavioral labels, not hiring outcomes."""

from __future__ import annotations

PRODUCT_ACTIONS = ("shortlist", "reject", "review")
BINARY_ACTIONS = ("shortlist", "reject")
REASON_CODES = (
    "skill_gap",
    "experience_gap",
    "education_mismatch",
    "strong_skill_match",
    "strong_project_evidence",
    "insufficient_evidence",
    "other",
)

RECRUITER_SHORTLISTED = "recruiter_shortlisted"
RECRUITER_REJECTED = "recruiter_rejected"
RECRUITER_REVIEWED = "recruiter_reviewed"
DATASET_SNAPSHOT_CREATED = "dataset_snapshot_created"
