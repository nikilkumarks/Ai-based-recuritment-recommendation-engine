"""Raw skill-span extraction via lexicon + spaCy PhraseMatcher. Not ontology matching."""

from __future__ import annotations

import re

from app.modules.nlp.constants import GENERIC_NON_SKILLS
from app.modules.nlp.lexicon import SKILL_LEXICON, surface_normalize
from app.modules.nlp.schemas import SkillMention
from app.modules.nlp.spacy_engine import get_nlp


def extract_skills(text: str, *, source_section: str | None = None) -> list[SkillMention]:
    if not text.strip():
        return []
    mentions: list[SkillMention] = []
    seen: set[tuple[int, int, str]] = set()
    for start, end, raw in _lexicon_spans(text):
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
    nlp, matcher = get_nlp()
    doc = nlp(text)
    for _match_id, start_token, end_token in matcher(doc):
        span = doc[start_token:end_token]
        raw = text[span.start_char : span.end_char]
        if surface_normalize(raw) in GENERIC_NON_SKILLS:
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
