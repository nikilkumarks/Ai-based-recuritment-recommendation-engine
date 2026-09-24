"""Raw skill-span extraction via lexicon + spaCy PhraseMatcher. Not ontology matching."""

from __future__ import annotations

import re

from app.modules.nlp.constants import GENERIC_NON_SKILLS, is_metadata_or_non_skill
from app.modules.nlp.lexicon import SKILL_LEXICON, surface_normalize
from app.modules.nlp.schemas import SkillMention
from app.modules.nlp.spacy_engine import get_nlp


def extract_skills(text: str, *, source_section: str | None = None) -> list[SkillMention]:
    if not text.strip():
        return []
    mentions: list[SkillMention] = []
    seen: set[tuple[int, int, str]] = set()

    # 1. Check category-structured lines (e.g. "Languages: JavaScript, Python", "Frontend: React, Next.js")
    for start, end, raw in _category_spans(text):
        if is_metadata_or_non_skill(raw):
            continue
        key = (start, end, raw.casefold())
        if key in seen:
            continue
        seen.add(key)
        mentions.append(
            SkillMention(
                raw_text=raw,
                normalized_text=surface_normalize(raw),
                source_section=source_section,
                evidence=raw,
                start=start,
                end=end,
                extraction_confidence=0.95,
            )
        )

    # 2. Check explicit lexicon patterns
    for start, end, raw in _lexicon_spans(text):
        if is_metadata_or_non_skill(raw):
            continue
        key = (start, end, raw.casefold())
        if key in seen:
            continue
        seen.add(key)
        mentions.append(
            SkillMention(
                raw_text=raw,
                normalized_text=surface_normalize(raw),
                source_section=source_section,
                evidence=raw,
                start=start,
                end=end,
                extraction_confidence=0.9,
            )
        )

    # 3. Check spaCy PhraseMatcher
    nlp, matcher = get_nlp()
    doc = nlp(text)
    for _match_id, start_token, end_token in matcher(doc):
        span = doc[start_token:end_token]
        raw = text[span.start_char : span.end_char]
        if is_metadata_or_non_skill(raw):
            continue
        key = (span.start_char, span.end_char, raw.casefold())
        if key in seen:
            continue
        seen.add(key)
        mentions.append(
            SkillMention(
                raw_text=raw,
                normalized_text=surface_normalize(raw),
                source_section=source_section,
                evidence=raw,
                start=span.start_char,
                end=span.end_char,
                extraction_confidence=0.85,
            )
        )
    mentions.sort(key=lambda item: (item.start or 0, -(item.end or 0)))
    return mentions


def _category_spans(text: str) -> list[tuple[int, int, str]]:
    found: list[tuple[int, int, str]] = []
    lines = text.split("\n")
    char_offset = 0
    ignored_headers = {
        "http",
        "https",
        "note",
        "description",
        "experience",
        "projects",
        "education",
        "certifications",
        "work history",
        "employment",
        "summary",
    }
    for line in lines:
        line_len = len(line)
        # Check pattern: "Category Name: Skill1, Skill2, Skill3" (Must have explicit colon :)
        match = re.match(r"^\s*([A-Za-z0-9\s&/\+]{2,30})\s*[:]\s*(.+)$", line)
        if match:
            cat_header = match.group(1).strip().casefold()
            if cat_header not in ignored_headers and len(match.group(1)) <= 30:
                skills_part = match.group(2).strip()
                # Split skills by commas, bullet separators
                items = re.split(r"[,;•|]", skills_part)
                for item in items:
                    clean_item = item.strip().rstrip(".")
                    if clean_item and 2 <= len(clean_item) <= 50 and not _is_sentence(clean_item):
                        # Find exact span in line
                        item_idx = line.find(clean_item)
                        if item_idx != -1:
                            start = char_offset + item_idx
                            end = start + len(clean_item)
                            found.append((start, end, clean_item))
        char_offset += line_len + 1
    return found


def _is_sentence(text: str) -> bool:
    return len(text.split()) > 6 or bool(re.search(r"\b(and|the|with|for|using|built|created|designed)\b", text, re.I))


def _lexicon_spans(text: str) -> list[tuple[int, int, str]]:
    found: list[tuple[int, int, str]] = []
    for term in sorted(SKILL_LEXICON, key=len, reverse=True):
        pattern = _term_pattern(term)
        for match in pattern.finditer(text):
            found.append((match.start(), match.end(), match.group(0)))
    return _drop_overlaps(found)


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    if re.search(r"[^\w\s]", term):
        return re.compile(escaped, re.I)
    return re.compile(rf"\b{escaped}\b", re.I)


def _drop_overlaps(spans: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    kept: list[tuple[int, int, str]] = []
    occupied: list[tuple[int, int]] = []
    for start, end, raw in sorted(spans, key=lambda item: (item[0], -(item[1] - item[0]))):
        if any(not (end <= left or start >= right) for left, right in occupied):
            continue
        occupied.append((start, end))
        kept.append((start, end, raw))
    return kept
