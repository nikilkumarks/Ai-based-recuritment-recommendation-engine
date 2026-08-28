from __future__ import annotations

from app.modules.nlp.pipeline import extract_job_draft, extract_profile_draft
from tests.fixtures.nlp_corpus import ANNOTATED_JD, ANNOTATED_RESUME, FALSE_POSITIVE_TEXT


def test_sections_detected() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    for name in ("summary", "experience", "education", "projects", "certifications", "skills"):
        assert name in draft.sections


def test_skills_extracted_without_equivalence() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    raw = {item.raw_text for item in draft.skills}
    for term in ["ML", "Machine Learning", "Python", "TensorFlow", "C++", "Node.js", "Next.js", "CI/CD"]:
        assert any(term.casefold() == value.casefold() for value in raw), term
    ml = [item for item in draft.skills if item.raw_text.upper() == "ML"]
    machine = [item for item in draft.skills if item.raw_text.casefold() == "machine learning"]
    assert ml and machine
    assert ml[0].normalized_text != machine[0].normalized_text
    assert all(item.evidence and item.source_section for item in draft.skills)


def test_generic_nouns_are_not_skills() -> None:
    draft = extract_profile_draft(FALSE_POSITIVE_TEXT)
    raw = {item.normalized_text for item in draft.skills}
    assert "project" not in raw
    assert "performance" not in raw


def test_experience_title_employer_dates_current() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    assert draft.experience
    first = draft.experience[0]
    assert first.job_title and "Engineer" in first.job_title
    assert first.employer and "Example" in first.employer
    assert first.is_current is True
    assert first.start_date is not None
    assert first.end_date is None
    assert first.evidence


def test_education_degree_field_institution() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    assert draft.education
    edu = draft.education[0]
    assert edu.degree
    assert edu.field_of_study and "Computer Science" in edu.field_of_study
    assert edu.institution
    assert edu.evidence


def test_projects_name_description_tech_url() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    assert draft.projects
    project = draft.projects[0]
    assert "Recommendation" in (project.name or "")
    assert project.description
    assert project.url and project.url.startswith("https://")
    tech = {item.raw_text.casefold() for item in project.technologies}
    assert "python" in tech
    assert project.evidence


def test_certification_name_issuer() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    assert draft.certifications
    cert = draft.certifications[0]
    assert "Cloud Practitioner" in (cert.name or "")
    assert cert.issuing_organization
    assert cert.evidence


def test_summary_is_extracted_not_generated() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    assert draft.summary
    assert "retrieval systems" in draft.summary.lower()


def test_contact_extracted() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    assert draft.contact.email == "ada@example.com"
    assert draft.contact.linkedin_url
    assert draft.contact.github_url


def test_job_requirements_raw_skills() -> None:
    draft = extract_job_draft(ANNOTATED_JD, fallback_title="Fallback")
    required = {item.raw_text.casefold() for item in draft.required_skills}
    preferred = {item.raw_text.casefold() for item in draft.preferred_skills}
    assert "python" in required
    assert "fastapi" in required
    assert "tensorflow" in preferred
    assert draft.min_years_experience == 4
    assert draft.education_level == "bachelor"
    assert draft.location
    assert draft.nlp_pipeline_version.startswith("nlp-")


def test_pipeline_version_present() -> None:
    draft = extract_profile_draft(ANNOTATED_RESUME)
    assert draft.nlp_pipeline_version == "nlp-v1"


def test_nlp_module_does_not_import_ml() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "modules" / "nlp"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "app.modules.ml" not in text
        assert "from app.modules import ml" not in text
