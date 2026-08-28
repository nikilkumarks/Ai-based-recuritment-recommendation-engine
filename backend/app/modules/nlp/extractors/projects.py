"""Project extraction. Technologies stay as raw mentions; no relevance scoring."""

from __future__ import annotations

import re

from app.modules.nlp.dates import parse_range
from app.modules.nlp.extractors.contact import _safe_http_url
from app.modules.nlp.extractors.skills import extract_skills
from app.modules.nlp.preprocess import line_blocks
from app.modules.nlp.schemas import EvidenceSpan, ProjectDraft

_URL = re.compile(r"https?://[^\s<>\[\]()]+", re.I)


def extract_projects(section: str) -> list[ProjectDraft]:
    items: list[ProjectDraft] = []
    for block in line_blocks(section) or [section]:
        item = _parse_block(block)
        if item is not None and item.name:
            items.append(item)
    return items


def _parse_block(block: str) -> ProjectDraft | None:
    lines = [line.strip() for line in block.split("\n") if line.strip()]
    if not lines:
        return None
    name = lines[0]
    if len(name) > 120:
        return None
    url = None
    url_match = _URL.search(block)
    if url_match:
        url = _safe_http_url(url_match.group(0))
    start, end, _is_current, raw_range = parse_range(block)
    desc_lines = [line for line in lines[1:] if not _URL.search(line) and not parse_range(line)[3]]
    description = "\n".join(desc_lines).strip() or None
    techs = extract_skills(block, source_section="projects")
    evidence = [
        EvidenceSpan(
            value=name,
            source_section="projects",
            evidence=block[:400],
            extraction_confidence=0.65,
        )
    ]
    if raw_range:
        evidence.append(
            EvidenceSpan(value=raw_range, source_section="projects", evidence=raw_range)
        )
    return ProjectDraft(
        name=name,
        description=description,
        url=url,
        technologies=techs,
        start_date=start,
        end_date=end,
        evidence=evidence,
    )
