"""Deterministic NLP pipeline. Independent from the ML module."""

from __future__ import annotations

from app.modules.nlp.constants import nlp_version
from app.modules.nlp.extractors import (
    extract_certifications,
    extract_contact,
    extract_education,
    extract_experience,
    extract_job_requirements,
    extract_projects,
    extract_skills,
    extract_summary,
)
from app.modules.nlp.preprocess import preprocess_document_text
from app.modules.nlp.schemas import ProfileDraft, SkillMention
from app.modules.nlp.sections import detect_sections, section_or_full
from app.modules.nlp.spacy_engine import warm_nlp


def extract_profile_draft(text: str, *, parser_version: str | None = None) -> ProfileDraft:
    cleaned = preprocess_document_text(text)
    sections = detect_sections(cleaned)
    summary_text = sections.get("summary") or ""
    summary, _summary_evidence = extract_summary(summary_text)
    skills_text = section_or_full(sections, "skills", cleaned)
    experience_text = sections.get("experience") or ""
    education_text = sections.get("education") or ""
    projects_text = sections.get("projects") or ""
    certs_text = sections.get("certifications") or ""

    skills = extract_skills(skills_text, source_section="skills" if "skills" in sections else "full")
    if "experience" in sections:
        skills = _merge_skills(skills, extract_skills(experience_text, source_section="experience"))
    if "projects" in sections:
        skills = _merge_skills(skills, extract_skills(projects_text, source_section="projects"))

    exp_list = extract_experience(experience_text) if experience_text else []
    if not exp_list:
        exp_list = extract_experience(cleaned)

    proj_list = extract_projects(projects_text) if projects_text else []
    if not proj_list:
        proj_list = extract_projects(cleaned)

    edu_list = extract_education(education_text) if education_text else []
    if not edu_list:
        edu_list = extract_education(cleaned)

    draft = ProfileDraft(
        summary=summary,
        contact=extract_contact(cleaned),
        skills=skills,
        experience=exp_list,
        education=edu_list,
        projects=proj_list,
        certifications=extract_certifications(certs_text) if certs_text else [],
        sections=sections,
        nlp_pipeline_version=nlp_version(),
        parser_version=parser_version,
        warnings=[],
    )
    if not sections:
        draft.warnings.append("Section headings were uncertain; raw text was preserved.")
    if not draft.skills:
        draft.warnings.append("No lexicon skill mentions were found.")
    return draft


def extract_job_draft(text: str, *, fallback_title: str | None = None):
    cleaned = preprocess_document_text(text)
    return extract_job_requirements(
        cleaned, nlp_pipeline_version=nlp_version(), fallback_title=fallback_title
    )


def _merge_skills(base: list[SkillMention], extra: list[SkillMention]) -> list[SkillMention]:
    seen = {(item.normalized_text, item.start, item.end) for item in base}
    merged = list(base)
    for item in extra:
        key = (item.normalized_text, item.start, item.end)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


__all__ = ["extract_job_draft", "extract_profile_draft", "warm_nlp"]
