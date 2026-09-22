"""Label and dataset policies. Recruiter actions are not hiring outcomes."""

from __future__ import annotations

LABEL_POLICY_VERSION = "label-policy-v1"
DATASET_SOURCE = "recruiter_decisions"
SUPPORTED_FEATURE_SCHEMAS = ("feature-schema-v1", "feature-schema-v2")
BINARY_POSITIVE = "shortlist"
BINARY_NEGATIVE = "reject"
EXCLUDED_ACTIONS = ("review", "view", "compare", "hire")

LEAKAGE_KEYS = {
    "label",
    "decision",
    "action",
    "shortlist",
    "reject",
    "review",
    "hire",
    "reason",
    "recruiter_reason",
    "note",
    "decision_note",
    "recruiter_id",
    "decision_id",
    "decision_time",
}

PROTECTED_KEYS = {
    "gender",
    "religion",
    "caste",
    "race",
    "ethnicity",
    "disability",
    "age",
    "marital_status",
    "name",
    "address",
    "college_prestige",
    "college",
}

GROUPING_KEYS = {"job_id", "candidate_id"}
