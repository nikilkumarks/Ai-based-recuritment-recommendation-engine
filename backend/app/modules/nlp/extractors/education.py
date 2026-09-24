"""Education extraction. No prestige or academic-quality inference."""

from __future__ import annotations

import re

from app.modules.nlp.constants import DEGREE_PATTERNS
from app.modules.nlp.dates import parse_range
from app.modules.nlp.preprocess import line_blocks
from app.modules.nlp.schemas import EducationDraft, EvidenceSpan

_INSTITUTION = re.compile(
    r"(?P<institution>(?:[A-Z][\w.&'\-]+(?:\s+[A-Z][\w.&'\-]+){0,8})\s+"
    r"(?:University|Institute|College|School)\b"
    r"|\b(?:University|Institute|College|School)\s+of\s+[A-Z][\w.&'\- ]{2,60})",
)

_FIELD = re.compile(
    r"\b(information science(?:\s+and\s+technology)?|information technology|"
    r"computer science(?:\s+and\s+engineering)?|computer engineering|"
    r"software engineering|data science|artificial intelligence|cyber security|"
    r"electronics(?:\s+and\s+communication)?|mechanical|electrical|civil|"
    r"business administration|management|finance|accounting|economics|physics|mathematics)\b",
    re.I,
)

_CGPA_RE = re.compile(r"\b(?:cgpa|gpa|percentage|score|marks?)\s*[:\-]?\s*([0-9.]+(?:\s*/\s*[0-9.]+)?)%?", re.I)


def extract_education(section: str) -> list[EducationDraft]:
    items: list[EducationDraft] = []
    for block in line_blocks(section) or [section]:
        item = _parse_block(block)
        if item is not None and (item.institution or item.degree):
            items.append(item)
    return items


def _parse_block(block: str) -> EducationDraft | None:
    start, end, _is_current, raw_range = parse_range(block)
    degree = None
    level = None
    for pattern, mapped in DEGREE_PATTERNS:
        match = re.search(pattern, block, re.I)
        if match:
            degree = match.group(0)
            level = mapped
            break
    institution = None
    inst_match = _INSTITUTION.search(block)
    if inst_match:
        institution = re.sub(r"\s+", " ", inst_match.group("institution")).strip(" ,")

    # If institution not matched by strict regex, check lines for University/College/Institute or line 0
    if not institution:
        for line in block.split("\n"):
            cleaned = line.strip(" ,")
            if re.search(r"\b(University|Institute|College|School|Academy)\b", cleaned, re.I):
                institution = cleaned
                break

    field = None
    field_match = _FIELD.search(block)
    if field_match:
        field = field_match.group(0)
    else:
        # Check if line contains Degree, Field of Study
        degree_line_match = re.search(
            r"(?:b\.?tech|b\.?e\.?|b\.?sc|m\.?tech|mca|m\.?s\.?|mba|phd)\s*[\-–—,:]\s*([A-Za-z\s&]{3,50})",
            block,
            re.I,
        )
        if degree_line_match:
            field = degree_line_match.group(1).strip(" -–|:,")

    cgpa_match = _CGPA_RE.search(block)
    cgpa_text = cgpa_match.group(0) if cgpa_match else None

    if not institution and not degree:
        return None

    evidence = [
        EvidenceSpan(
            value=institution or degree,
            source_section="education",
            evidence=f"{block[:300]} (CGPA: {cgpa_text})" if cgpa_text else block[:400],
            extraction_confidence=0.85 if institution and degree else 0.6,
        )
    ]
    if raw_range:
        evidence.append(
            EvidenceSpan(
                value=raw_range,
                source_section="education",
                evidence=raw_range,
                extraction_confidence=0.75,
            )
        )
    return EducationDraft(
        institution=institution,
        degree=degree,
        field_of_study=field,
        education_level=level,
        start_date=start,
        end_date=end,
        evidence=evidence,
    )
