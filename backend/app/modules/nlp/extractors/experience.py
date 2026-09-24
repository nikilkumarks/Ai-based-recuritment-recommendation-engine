"""Experience extraction. Does not invent titles, employers, or dates."""

from __future__ import annotations

import re

from app.modules.nlp.dates import parse_range, years_between
from app.modules.nlp.preprocess import line_blocks
from app.modules.nlp.schemas import EvidenceSpan, ExperienceDraft

_AT = re.compile(r"^(?P<title>.+?)\s+at\s+(?P<employer>.+)$", re.I)
_PIPE = re.compile(r"^(?P<title>[^|]+)\|\s*(?P<employer>[^|]+?)(?:\|\s*(?P<rest>.+))?$")
_DASH = re.compile(r"^(?P<title>[^\-–—]+)\s*[\-–—]\s*(?P<employer>[^\-–—]+?)(?:\s*[\-–—]\s*(?P<rest>.+))?$")
_COMMA = re.compile(r"^(?P<title>[^,]+),\s*(?P<employer>[^,]+)$")

_ROLE_KEYWORDS = re.compile(
    r"\b(developer|engineer|intern|freelancer?|freelance|manager|consultant|architect|lead|designer|analyst|specialist|administrator|coordinator|director|officer|executive|assistant|founder|co-founder|head|lead)\b",
    re.I,
)


def extract_experience(section: str) -> list[ExperienceDraft]:
    items: list[ExperienceDraft] = []
    for block in _experience_blocks(section):
        item = _parse_block(block)
        if item is not None and (item.job_title or item.employer):
            items.append(item)
    return items


def _experience_blocks(section: str) -> list[str]:
    raw_blocks = line_blocks(section) or [section]
    chunks: list[str] = []
    for block in raw_blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        sub_chunks: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            if _looks_like_role_start(line) and current:
                sub_chunks.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            sub_chunks.append(current)
        for chunk in sub_chunks:
            chunks.append("\n".join(chunk))
    return chunks


def _looks_like_role_start(line: str) -> bool:
    cleaned = re.sub(r"^(?:[\d\.\-\*•\[\]]+\s*)+", "", line).strip()
    if not cleaned:
        return False
    if parse_range(cleaned)[3]:
        return False
    if line.strip().startswith(("-", "*", "•")):
        return False
    if re.match(r"^\d+[\.\)]\s+[A-Z]", line.strip()):
        return True
    if re.search(r"\sat\s", cleaned, re.I):
        return True
    if "|" in cleaned or " – " in cleaned or " - " in cleaned or " — " in cleaned:
        if not parse_range(cleaned)[3]:
            return True
    if _ROLE_KEYWORDS.search(cleaned) and len(cleaned) < 80:
        return True
    return False


def _clean_line(text: str) -> str:
    cleaned = re.sub(r"^(?:[\d\.\-\*•\[\]]+\s*)+", "", text).strip()
    return cleaned.rstrip(" -–|:,").strip()


def _parse_block(block: str) -> ExperienceDraft | None:
    start, end, is_current, raw_range = parse_range(block)
    lines = [line.strip() for line in block.split("\n") if line.strip()]
    if not lines:
        return None

    header = _clean_line(lines[0])
    title = None
    employer = None

    for pattern in (_AT, _PIPE, _DASH, _COMMA):
        match = pattern.match(header)
        if match:
            t_cand = match.group("title").strip(" -–|,")
            e_cand = match.group("employer").strip(" -–|,")
            if not parse_range(e_cand)[3]:
                title = t_cand
                employer = e_cand
                break

    if title is None and employer is None:
        if len(lines) >= 2 and not parse_range(lines[0])[3] and len(header) < 90:
            second_line = _clean_line(lines[1])
            if parse_range(second_line)[3]:
                title = header
            elif len(second_line) < 90 and not second_line.startswith(("http", "www", "•", "-")):
                if _ROLE_KEYWORDS.search(header):
                    title = header
                    employer = second_line
                elif _ROLE_KEYWORDS.search(second_line):
                    title = second_line
                    employer = header
                else:
                    title = header
                    employer = second_line
            else:
                title = header
        elif header and not parse_range(header)[3] and len(header) < 90:
            title = header

    if not title and not employer:
        return None

    title = _clean_line(title) if title else None
    employer = _clean_line(employer) if employer else None

    description_lines = []
    for line in lines:
        cleaned_l = _clean_line(line)
        if parse_range(line)[3]:
            continue
        if title and cleaned_l == title:
            continue
        if employer and cleaned_l == employer:
            continue
        if header and cleaned_l == header:
            continue
        description_lines.append(line)

    description = "\n".join(description_lines).strip() or None

    evidence = [
        EvidenceSpan(
            value=title or employer or header,
            source_section="experience",
            evidence=block[:400],
            extraction_confidence=0.85 if title and employer else 0.65,
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
