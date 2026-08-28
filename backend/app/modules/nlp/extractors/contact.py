"""Contact extraction. Treat as PII — callers must not log these values."""

from __future__ import annotations

import re

from app.modules.nlp.constants import EMAIL_RE, PHONE_RE, URL_RE
from app.modules.nlp.schemas import ContactDraft, EvidenceSpan

_EMAIL = re.compile(EMAIL_RE, re.I)
_PHONE = re.compile(PHONE_RE)
_URL = re.compile(URL_RE, re.I)


def _safe_http_url(raw: str) -> str | None:
    cleaned = raw.rstrip(".,);]")
    lowered = cleaned.lower()
    if not lowered.startswith(("http://", "https://")):
        return None
    if lowered.startswith(("javascript:", "data:", "file:")):
        return None
    return cleaned


def extract_contact(text: str) -> ContactDraft:
    contact = ContactDraft()
    header = "\n".join(text.split("\n")[:12])
    email = _EMAIL.search(header) or _EMAIL.search(text)
    if email:
        contact.email = email.group(0)
        contact.evidence.append(
            EvidenceSpan(
                value=email.group(0),
                source_section="header",
                evidence=email.group(0),
                start=email.start(),
                end=email.end(),
                extraction_confidence=0.95,
            )
        )
    phone = _PHONE.search(header)
    if phone and sum(ch.isdigit() for ch in phone.group(0)) >= 10:
        contact.phone = re.sub(r"\s+", " ", phone.group(0)).strip()
        contact.evidence.append(
            EvidenceSpan(
                value=contact.phone,
                source_section="header",
                evidence=phone.group(0),
                start=phone.start(),
                end=phone.end(),
                extraction_confidence=0.7,
            )
        )
    for match in _URL.finditer(text):
        url = _safe_http_url(match.group(0))
        if url is None:
            continue
        lowered = url.lower()
        span = EvidenceSpan(
            value=url,
            source_section="header",
            evidence=url,
            start=match.start(),
            end=match.end(),
            extraction_confidence=0.9,
        )
        if "linkedin.com" in lowered and contact.linkedin_url is None:
            contact.linkedin_url = url
            contact.evidence.append(span)
        elif "github.com" in lowered and contact.github_url is None:
            contact.github_url = url
            contact.evidence.append(span)
        elif contact.portfolio_url is None and "linkedin.com" not in lowered and "github.com" not in lowered:
            contact.portfolio_url = url
            contact.evidence.append(span)
    return contact
