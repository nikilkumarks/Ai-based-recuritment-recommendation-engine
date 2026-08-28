"""Baseline matching constants. Not trained weights and not accuracy claims."""

from __future__ import annotations

FEATURE_SCHEMA_VERSION = "feature-schema-v1"
FEATURE_SCHEMA_V2 = "feature-schema-v2"
SNAPSHOT_FEATURE_SCHEMA_VERSION = FEATURE_SCHEMA_V2
WEIGHT_SET_VERSION = "baseline-weights-v1"
SCORING_MODE_BASELINE = "baseline"

# Required-skill coverage counts exact canonical/alias matches only.
# Child, parent, and related evidence are traces/gaps, not satisfied requirements.
CHILD_REQUIRED_CREDIT = 0.0
PARENT_REQUIRED_CREDIT = 0.0
RELATED_REQUIRED_CREDIT = 0.0

SCORE_MIN = 0.0
SCORE_MAX = 1.0
SCORE_DECIMALS = 4
PERSISTED_SCORE_DECIMALS = 2

DEFAULT_WEIGHT_REQUIRED = 0.60
DEFAULT_WEIGHT_PREFERRED = 0.10
DEFAULT_WEIGHT_SEMANTIC = 0.15
DEFAULT_WEIGHT_EXPERIENCE = 0.10
DEFAULT_WEIGHT_EDUCATION_PROJECT = 0.05

# Baseline heuristics for project/experience embedding evidence. Not validated thresholds.
DEFAULT_PROJECT_COSINE_THRESHOLD = 0.45
DEFAULT_EXPERIENCE_COSINE_THRESHOLD = 0.45
