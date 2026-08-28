"""Summary/objective extraction. Extracts existing text; does not generate a rewrite."""

from __future__ import annotations

from app.modules.nlp.schemas import EvidenceSpan


def extract_summary(section: str) -> tuple[str | None, list[EvidenceSpan]]:
    cleaned = section.strip()
    if not cleaned:
        return None, []
    # Use the first 1–3 sentences/lines already present. Never invent prose.
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
    summary = " ".join(lines[:4]).strip()
    if len(summary) < 20:
        return None, []
    return summary, [
        EvidenceSpan(
            value=summary[:200],
            source_section="summary",
            evidence=summary[:400],
            extraction_confidence=0.8,
        )
    ]
