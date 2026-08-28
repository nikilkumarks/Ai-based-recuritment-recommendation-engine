"""Candidate-visibility modes. The campus vs org-private pool decision is still open."""

from __future__ import annotations

from enum import Enum

from app.core.config import get_settings


class CandidateVisibilityMode(str, Enum):
    """Configurable later without rewriting routers.

    - applicants_and_opted_in: default. Applicants to the recruiter's org jobs, plus
      candidates who set preferences.discoverable = true.
    - applicants_only: org-private talent pool.
    - shared_campus_pool: any recruiter may view any candidate (campus-wide).
    """

    APPLICANTS_AND_OPTED_IN = "applicants_and_opted_in"
    APPLICANTS_ONLY = "applicants_only"
    SHARED_CAMPUS_POOL = "shared_campus_pool"


def current_visibility_mode() -> CandidateVisibilityMode:
    raw = get_settings().candidate_visibility_mode.strip().lower()
    try:
        return CandidateVisibilityMode(raw)
    except ValueError:
        return CandidateVisibilityMode.APPLICANTS_AND_OPTED_IN


def candidate_opted_into_discovery(preferences: dict | None) -> bool:
    if not preferences:
        return False
    return bool(preferences.get("discoverable"))
