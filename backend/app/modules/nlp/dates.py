"""Conservative date parsing. Ambiguous values stay null with evidence preserved."""

from __future__ import annotations

import re
from datetime import date

from app.modules.nlp.constants import MONTH_MAP, PRESENT_TOKENS

_MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
)
_YEAR = r"(?:19|20)\d{2}"
_PRESENT = r"(?:Present|Current|Now|Ongoing)"
RANGE_RE = re.compile(
    rf"(?P<left>{_MONTH}\s+{_YEAR}|{_YEAR})\s*(?:-|–|—|to)\s*(?P<right>{_MONTH}\s+{_YEAR}|{_YEAR}|{_PRESENT})",
    re.I,
)
TOKEN_RE = re.compile(rf"({_MONTH}\s+{_YEAR}|{_YEAR})", re.I)


def parse_month_year(token: str) -> date | None:
    cleaned = token.strip()
    if cleaned.casefold() in PRESENT_TOKENS:
        return None
    parts = cleaned.replace(",", " ").split()
    if len(parts) == 1 and re.fullmatch(_YEAR, parts[0]):
        return date(int(parts[0]), 1, 1)
    if len(parts) == 2:
        month = MONTH_MAP.get(parts[0].casefold())
        if month and re.fullmatch(_YEAR, parts[1]):
            return date(int(parts[1]), month, 1)
    return None


def parse_range(text: str) -> tuple[date | None, date | None, bool, str | None]:
    """Return start, end, is_current, raw_match. Unparsed dates stay None."""
    match = RANGE_RE.search(text)
    if not match:
        return None, None, False, None
    raw = match.group(0)
    left = match.group("left")
    right = match.group("right")
    start = parse_month_year(left)
    is_current = right.casefold() in PRESENT_TOKENS
    end = None if is_current else parse_month_year(right)
    return start, end, is_current, raw


def years_between(start: date | None, end: date | None, *, is_current: bool) -> float | None:
    if start is None:
        return None
    finish = date.today() if is_current and end is None else end
    if finish is None:
        return None
    months = (finish.year - start.year) * 12 + (finish.month - start.month)
    if months < 0:
        return None
    return round(months / 12.0, 2)
