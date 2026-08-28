"""Rule-based resume/JD section detection. Not semantic NLP."""

from __future__ import annotations

from app.modules.documents.processor import detect_sections as detect_resume_sections


def detect_sections(text: str) -> dict[str, str]:
    found = detect_resume_sections(text)
    return dict(found or {})


def section_or_full(sections: dict[str, str], name: str, full_text: str) -> str:
    value = sections.get(name)
    if value:
        return value
    return full_text


JOB_SECTION_ALIASES = {
    "required": ("requirements", "required", "must have", "minimum qualifications"),
    "preferred": ("preferred", "nice to have", "good to have", "optional"),
    "about": ("about the role", "the role", "overview", "summary"),
}


def detect_job_sections(text: str) -> dict[str, str]:
    """Split a JD on conservative headings. Uncertain text stays in 'full'."""
    lines = text.split("\n")
    hits: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        key = _job_heading(line)
        if key:
            hits.append((index, key))
    sections: dict[str, str] = {"full": text}
    if len(hits) < 1:
        return sections
    for i, (start, key) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(lines)
        body = "\n".join(lines[start + 1 : end]).strip()
        if body:
            sections[key] = body
    return sections


def _job_heading(line: str) -> str | None:
    stripped = line.strip().rstrip(":").lower()
    if not stripped or len(stripped) > 48:
        return None
    for key, aliases in JOB_SECTION_ALIASES.items():
        if stripped in aliases:
            return key
    return None
