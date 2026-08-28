"""Deterministic embedding source text. Versioned; not a match score."""

from __future__ import annotations

from collections.abc import Iterable

from app.models import (
    CandidateProfile,
    CandidateSkill,
    ExperienceItem,
    Job,
    JobPreferredSkill,
    JobRequiredSkill,
    JobRequirement,
    ProjectItem,
)
from app.modules.embeddings.hashing import normalize_source_text
from app.modules.embeddings.version import resolved_text_version


def text_version() -> str:
    return resolved_text_version()


def build_profile_text(profile: CandidateProfile) -> str:
    payload = profile.extracted_payload or {}
    lines = [f"Summary: {profile.summary or payload.get('summary') or ''}"]
    skills = _skill_names(profile.skills)
    if skills:
        lines.append("Skills: " + ", ".join(skills))
    for item in profile.experience_items:
        lines.append("Experience: " + build_experience_text(item, payload=payload))
    for item in profile.project_items:
        lines.append("Project: " + build_project_text(item, payload=payload))
    for item in profile.education_items:
        parts = [item.degree, item.field_of_study, item.institution]
        lines.append("Education: " + ", ".join(part for part in parts if part))
    for item in profile.certification_items:
        parts = [item.name, item.issuing_organization]
        lines.append("Certification: " + ", ".join(part for part in parts if part))
    return normalize_source_text("\n".join(lines))


def build_experience_text(item: ExperienceItem, *, payload: dict | None = None) -> str:
    techs = _tech_for(payload or {}, "experience", item.job_title)
    parts = [item.job_title, item.employer, item.description, techs]
    return normalize_source_text(". ".join(part for part in parts if part))


def build_project_text(item: ProjectItem, *, payload: dict | None = None) -> str:
    techs = _tech_for(payload or {}, "projects", item.name)
    parts = [item.name, item.description, techs]
    return normalize_source_text(". ".join(part for part in parts if part))


def build_job_text(job: Job, requirement: JobRequirement | None) -> str:
    payload = requirement.extracted_payload if requirement is not None else {}
    payload = payload or {}
    lines = [f"Title: {job.title}", f"Description: {job.description_raw}"]
    if requirement is not None:
        required = _job_skill_names(requirement.required_skills)
        preferred = _job_skill_names(requirement.preferred_skills)
        if required:
            lines.append("Required skills: " + ", ".join(required))
        if preferred:
            lines.append("Preferred skills: " + ", ".join(preferred))
        if requirement.education_level:
            lines.append(f"Education: {requirement.education_level}")
        if requirement.min_years_experience is not None:
            lines.append(f"Years experience: {requirement.min_years_experience}")
    return normalize_source_text("\n".join(lines))


def build_job_requirement_text(job: Job, requirement: JobRequirement) -> str:
    """Canonical confirmed skills are the skill representation.

    Unmatched raw mentions stay as evidence only; they are never used as a
    fallback canonical skill list.
    """
    payload = requirement.extracted_payload or {}
    canonical_required = _skill_names_from_rows(requirement.required_skills)
    canonical_preferred = _skill_names_from_rows(requirement.preferred_skills)
    raw_required = _raw_names(payload.get("required_skills") or [])
    raw_preferred = _raw_names(payload.get("preferred_skills") or [])
    lines = [f"Title: {payload.get('title') or job.title}"]
    if canonical_required:
        lines.append("Required skills: " + ", ".join(canonical_required))
    if canonical_preferred:
        lines.append("Preferred skills: " + ", ".join(canonical_preferred))
    unmatched = _unmatched_mentions(raw_required, canonical_required) + _unmatched_mentions(
        raw_preferred, canonical_preferred
    )
    if unmatched:
        lines.append("Unmatched requirement mentions: " + ", ".join(unmatched))
    if requirement.min_years_experience is not None:
        lines.append(f"Years experience: {requirement.min_years_experience}")
    if requirement.education_level:
        lines.append(f"Education: {requirement.education_level}")
    return normalize_source_text("\n".join(lines))


def _skill_names(rows: Iterable[CandidateSkill]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        name = row.skill.canonical_name if row.skill is not None else None
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _job_skill_names(rows: Iterable[JobRequiredSkill] | Iterable[JobPreferredSkill]) -> list[str]:
    return _skill_names_from_rows(rows)


def _skill_names_from_rows(rows) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in rows or []:
        skill = getattr(row, "skill", None)
        name = skill.canonical_name if skill is not None else None
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _raw_names(rows: list[dict]) -> list[str]:
    names: list[str] = []
    for item in rows:
        value = item.get("raw_text") or item.get("canonical_skill_name")
        if value:
            names.append(str(value))
    return names


def _unmatched_mentions(raw_names: list[str], canonical_names: list[str]) -> list[str]:
    canonical = {name.casefold() for name in canonical_names}
    unmatched: list[str] = []
    seen: set[str] = set()
    for name in raw_names:
        key = name.casefold()
        if key in canonical or key in seen:
            continue
        seen.add(key)
        unmatched.append(name)
    return unmatched


def _tech_for(payload: dict, key: str, name: str | None) -> str:
    for item in payload.get(key) or []:
        label = item.get("name") or item.get("job_title")
        if name and label and str(label).casefold() == name.casefold():
            techs = item.get("technologies") or []
            labels = []
            for tech in techs:
                if isinstance(tech, dict):
                    labels.append(str(tech.get("raw_text") or ""))
                else:
                    labels.append(str(tech))
            return ", ".join(part for part in labels if part)
    return ""
