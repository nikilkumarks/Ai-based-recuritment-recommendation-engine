"""Job-description requirement extraction. Skills stay as raw mentions."""

from __future__ import annotations

import re

from app.modules.nlp.constants import DEGREE_PATTERNS, EMPLOYMENT_PATTERNS, SENIORITY_PATTERNS
from app.modules.nlp.extractors.skills import extract_skills
from app.modules.nlp.schemas import EvidenceSpan, JobRequirementsDraft, SkillMention
from app.modules.nlp.sections import detect_job_sections

_YEARS = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)\b", re.I)
_LOCATION = re.compile(r"location\s*:\s*(.+)$", re.I | re.M)
_TITLE = re.compile(r"(?:job\s+title|title)\s*:\s*(.+)$", re.I | re.M)


def extract_job_requirements(
    text: str, *, nlp_pipeline_version: str, fallback_title: str | None = None
) -> JobRequirementsDraft:
    sections = detect_job_sections(text)
    required_text = sections.get("required") or ""
    preferred_text = sections.get("preferred") or ""
    required = extract_skills(required_text, source_section="required") if required_text else []
    preferred = extract_skills(preferred_text, source_section="preferred") if preferred_text else []
    if not required and not preferred:
        required = extract_skills(text, source_section="full")
    required, preferred = _dedupe_preferred(required, preferred)

    years = None
    years_match = _YEARS.search(text)
    if years_match:
        years = float(years_match.group(1))

    education_level = _first_map(text, DEGREE_PATTERNS)
    seniority = _first_map(text, SENIORITY_PATTERNS)
    employment_type = _first_map(text, EMPLOYMENT_PATTERNS)

    location = None
    loc_match = _LOCATION.search(text)
    if loc_match:
        location = loc_match.group(1).strip()[:255]
    elif re.search(r"\bremote\b", text, re.I):
        location = "Remote"

    title = fallback_title
    title_match = _TITLE.search(text)
    if title_match:
        title = title_match.group(1).strip()[:255]
    if not title:
        first = text.strip().split("\n", 1)[0].strip()
        if 3 <= len(first) <= 80:
            title = first

    warnings: list[str] = []
    if not required:
        warnings.append("No required skill mentions were confidently extracted.")

    evidence = [
        EvidenceSpan(
            value=title,
            source_section="full",
            evidence=text[:240],
            extraction_confidence=0.6,
        )
    ]
    return JobRequirementsDraft(
        title=title,
        required_skills=required,
        preferred_skills=preferred,
        min_years_experience=years,
        education_level=education_level,
        seniority=seniority,
        location=location,
        employment_type=employment_type,
        nlp_pipeline_version=nlp_pipeline_version,
        warnings=warnings,
        evidence=evidence,
    )


def _first_map(text: str, patterns: tuple[tuple[str, str], ...]) -> str | None:
    for pattern, value in patterns:
        if re.search(pattern, text, re.I):
            return value
    return None


def _dedupe_preferred(
    required: list[SkillMention], preferred: list[SkillMention]
) -> tuple[list[SkillMention], list[SkillMention]]:
    required_keys = {item.normalized_text for item in required}
    preferred = [item for item in preferred if item.normalized_text not in required_keys]
    return required, preferred
