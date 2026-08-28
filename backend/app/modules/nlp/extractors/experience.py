"""Experience extraction. Does not invent titles, employers, or dates."""

from __future__ import annotations

import re

from app.modules.nlp.dates import parse_range, years_between
from app.modules.nlp.preprocess import line_blocks
from app.modules.nlp.schemas import EvidenceSpan, ExperienceDraft

_AT = re.compile(r"^(?P<title>.+?)\s+at\s+(?P<employer>.+)$", re.I)
_PIPE = re.compile(r"^(?P<title>[^|]+)\|\s*(?P<employer>[^|]+?)(?:\|\s*(?P<rest>.+))?$")
_COMMA = re.compile(r"^(?P<title>.+?),\s+(?P<employer>.+)$")


def extract_experience(section: str) -> list[ExperienceDraft]:
    items: list[ExperienceDraft] = []
    for block in _experience_blocks(section):
        item = _parse_block(block)
        if item is not None and (item.job_title or item.employer):
            items.append(item)
    return items


def _experience_blocks(section: str) -> list[str]:
    blocks = line_blocks(section)
    if len(blocks) >= 2:
        return blocks
    lines = [line.strip() for line in section.split("\n") if line.strip()]
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if _looks_like_role_start(line) and current:
            chunks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append(current)
    return ["\n".join(chunk) for chunk in chunks]


def _looks_like_role_start(line: str) -> bool:
    if re.search(r"\sat\s", line, re.I):
        return True
    if "|" in line:
        return True
    return False


def _parse_block(block: str) -> ExperienceDraft | None:
    start, end, is_current, raw_range = parse_range(block)
    lines = [line.strip() for line in block.split("\n") if line.strip()]
    if not lines:
        return None
    header = lines[0]
    title = None
    employer = None
    for pattern in (_AT, _PIPE, _COMMA):
        match = pattern.match(header)
        if match:
            title = match.group("title").strip(" -–|,")
            employer = match.group("employer").strip(" -–|,")
            break
    if title is None and len(lines) > 1 and not parse_range(header)[3]:
        title = header
    description_lines = []
    for line in lines[1:]:
        if parse_range(line)[3]:
            continue
        if line == header:
            continue
        description_lines.append(line)
    description = "\n".join(description_lines).strip() or None
    if not title and not employer:
        return None
    evidence = [
        EvidenceSpan(
            value=header,
            source_section="experience",
            evidence=block[:400],
            extraction_confidence=0.75 if title and employer else 0.55,
        )
    ]
    if raw_range:
        evidence.append(
            EvidenceSpan(
                value=raw_range,
                source_section="experience",
                evidence=raw_range,
                extraction_confidence=0.8,
            )
        )
    return ExperienceDraft(
        job_title=title,
        employer=employer,
        description=description,
        start_date=start,
        end_date=end,
        is_current=is_current,
        years_experience=years_between(start, end, is_current=is_current),
        evidence=evidence,
    )
