"""NLP pipeline version and conservative extraction constants.

NLP extraction is not semantic skill normalization.
"""

from __future__ import annotations

from app.core.config import get_settings

NLP_PIPELINE_VERSION = "nlp-v1"

EMAIL_RE = r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}"
PHONE_RE = r"(?:\+\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,5}[\s\-]?\d{4,6}"
URL_RE = r"https?://[^\s<>\[\]()]+"

MONTH_MAP = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

PRESENT_TOKENS = frozenset({"present", "current", "now", "ongoing"})

DEGREE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bb\.?\s*tech\b|\bbachelor of technology\b", "bachelor"),
    (r"\bb\.?\s*e\.?\b|\bbachelor of engineering\b", "bachelor"),
    (r"\bb\.?\s*sc\b|\bbachelor of science\b|\bbachelor'?s\b", "bachelor"),
    (r"\bm\.?\s*tech\b|\bmaster of technology\b", "master"),
    (r"\bmca\b|\bmaster of computer applications\b", "master"),
    (r"\bm\.?\s*s\.?\b|\bm\.?\s*sc\b|\bmaster of science\b|\bmaster'?s\b", "master"),
    (r"\bphd\b|\bph\.?\s*d\.?\b|\bdoctorate\b", "doctorate"),
    (r"\bmba\b", "master"),
)

SENIORITY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bintern\b|\binternship\b", "intern"),
    (r"\bjunior\b|\bentry[-\s]?level\b", "junior"),
    (r"\bmid[-\s]?level\b|\bintermediate\b", "mid"),
    (r"\bsenior\b|\bsr\.?\b", "senior"),
    (r"\bstaff\b", "staff"),
    (r"\bprincipal\b|\blead\b", "principal"),
)

EMPLOYMENT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bfull[-\s]?time\b", "full_time"),
    (r"\bpart[-\s]?time\b", "part_time"),
    (r"\bcontract\b|\bcontractor\b", "contract"),
    (r"\binternship\b", "internship"),
    (r"\bremote\b", "remote"),
)

GENERIC_NON_SKILLS = frozenset(
    {
        "project",
        "projects",
        "performance",
        "experience",
        "education",
        "summary",
        "team",
        "work",
        "system",
        "systems",
        "data",
        "software",
        "engineer",
        "engineering",
        "candidate",
        "resume",
    }
)


def nlp_version() -> str:
    return get_settings().nlp_pipeline_version
