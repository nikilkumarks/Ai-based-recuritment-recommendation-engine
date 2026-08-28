"""Certification extraction. Presence of a name does not imply validity."""

from __future__ import annotations

import re

from app.modules.nlp.dates import parse_month_year, parse_range
from app.modules.nlp.extractors.contact import _safe_http_url
from app.modules.nlp.preprocess import line_blocks
from app.modules.nlp.schemas import CertificationDraft, EvidenceSpan

_URL = re.compile(r"https?://[^\s<>\[\]()]+", re.I)
_ISSUER = re.compile(
    r"(?:issued by|issuer|from)\s+(?P<issuer>[A-Z][\w.&'\- ]{2,80})",
    re.I,
)
_COMMA_ISSUER = re.compile(
    r"^(?P<name>.+?),\s+(?P<issuer>Amazon Web Services|Google|Microsoft|AWS|Meta|Oracle|Cisco|CompTIA|.+?)"
    r"(?:,\s+(?P<rest>.+))?$",
    re.I,
)


def extract_certifications(section: str) -> list[CertificationDraft]:
    blocks = line_blocks(section)
    if not blocks:
        blocks = [line.strip() for line in section.split("\n") if line.strip()]
    items: list[CertificationDraft] = []
    for block in blocks:
        item = _parse_block(block)
        if item is not None and item.name:
            items.append(item)
    return items


def _parse_block(block: str) -> CertificationDraft | None:
    cleaned = block.strip()
    if not cleaned or len(cleaned) > 300:
        return None
    start, end, is_current, raw_range = parse_range(cleaned)
    if start is None:
        token = re.search(
            r"(January|February|March|April|May|June|July|August|September|"
            r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"\s+(?:19|20)\d{2}",
            cleaned,
            re.I,
        )
        if token:
            start = parse_month_year(token.group(0))
            raw_range = token.group(0)
    name = cleaned.split("\n")[0]
    issuer = None
    issuer_match = _ISSUER.search(cleaned)
    comma_match = _COMMA_ISSUER.match(name)
    if issuer_match:
        issuer = issuer_match.group("issuer").strip(" ,")
        name = cleaned[: issuer_match.start()].strip(" ,")
    elif comma_match:
        name = comma_match.group("name").strip()
        issuer = comma_match.group("issuer").strip()
    url = None
    url_match = _URL.search(cleaned)
    if url_match:
        url = _safe_http_url(url_match.group(0))
    name = re.sub(
        r",\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec).*$",
        "",
        name,
        flags=re.I,
    )
    name = name.strip(" ,-")
    if len(name) < 3:
        return None
    evidence = [
        EvidenceSpan(
            value=name,
            source_section="certifications",
            evidence=cleaned[:400],
            extraction_confidence=0.6,
        )
    ]
    if raw_range:
        evidence.append(
            EvidenceSpan(value=raw_range, source_section="certifications", evidence=raw_range)
        )
    return CertificationDraft(
        name=name,
        issuing_organization=issuer,
        issue_date=start,
        expiry_date=end if end and not is_current else None,
        credential_url=url,
        evidence=evidence,
    )
