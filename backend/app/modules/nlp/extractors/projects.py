"""Project extraction. Technologies stay as raw mentions; no relevance scoring."""

from __future__ import annotations

import re

from app.modules.nlp.dates import parse_range
from app.modules.nlp.extractors.contact import _safe_http_url
from app.modules.nlp.extractors.skills import extract_skills
from app.modules.nlp.preprocess import line_blocks
from app.modules.nlp.schemas import EvidenceSpan, ProjectDraft

_URL = re.compile(r"https?://[^\s<>\[\]()]+", re.I)
_PROJECT_START = re.compile(r"^(?:[\d\.\-\*•\[\]]+\s*)*([A-Z0-9][\w\s.\-\+&'\/]{2,60})(?:\s*[\-–—|:]\s*.*)?$")


def extract_projects(section: str) -> list[ProjectDraft]:
    items: list[ProjectDraft] = []
    for block in _project_blocks(section):
        item = _parse_block(block)
        if item is not None and item.name:
            items.append(item)
    return items


def _project_blocks(section: str) -> list[str]:
    raw_blocks = line_blocks(section) or [section]
    chunks: list[str] = []
    for block in raw_blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        sub_chunks: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            if _looks_like_project_start(line) and current:
                sub_chunks.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            sub_chunks.append(current)
        for chunk in sub_chunks:
            chunks.append("\n".join(chunk))
    return chunks


def _looks_like_project_start(line: str) -> bool:
    cleaned = re.sub(r"^(?:[\d\.\-\*•\[\]]+\s*)+", "", line).strip()
    if not cleaned:
        return False
    if parse_range(cleaned)[3]:
        return False
    if line.strip().startswith(("-", "*", "•")):
        return False
    if cleaned.casefold().startswith(("technologies:", "tech stack:", "features:", "tech:", "tools:")):
        return False
    if re.match(r"^\d+[\.\)]\s+[A-Z]", line.strip()):
        return True
    if " – " in cleaned or " - " in cleaned or " — " in cleaned or " | " in cleaned:
        first_word = cleaned.split()[0]
        if len(first_word) < 25:
            return True
    return False


def _clean_proj_name(text: str) -> str:
    cleaned = re.sub(r"^(?:[\d\.\-\*•\[\]]+\s*)+", "", text).strip()
    return cleaned.rstrip(" -–|:,").strip()


def _parse_block(block: str) -> ProjectDraft | None:
    lines = [line.strip() for line in block.split("\n") if line.strip()]
    if not lines:
        return None

    raw_header = lines[0]
    cleaned_header = _clean_proj_name(raw_header)
    if not cleaned_header or len(cleaned_header) > 140:
        return None

    name = cleaned_header
    tagline = None
    for sep in (" – ", " - ", " — ", " | "):
        if sep in cleaned_header:
            parts = cleaned_header.split(sep, 1)
            name = parts[0].strip()
            tagline = parts[1].strip()
            break

    # Strip badges like Live | GitHub from name
    name = re.sub(r"\s*(Live|GitHub|Demo|Link)\b.*$", "", name, flags=re.I).strip(" -–|:,")

    url = None
    url_match = _URL.search(block)
    if url_match:
        url = _safe_http_url(url_match.group(0))

    start, end, _is_current, raw_range = parse_range(block)

    desc_lines = []
    if tagline:
        desc_lines.append(tagline)

    for line in lines[1:]:
        if _URL.search(line) and len(line) < 100:
            continue
        if parse_range(line)[3]:
            continue
        desc_lines.append(line)

    description = "\n".join(desc_lines).strip() or None
    techs = extract_skills(block, source_section="projects")

    evidence = [
        EvidenceSpan(
            value=name,
            source_section="projects",
            evidence=block[:400],
            extraction_confidence=0.8,
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
