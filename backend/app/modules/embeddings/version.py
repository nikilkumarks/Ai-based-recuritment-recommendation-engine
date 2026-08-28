"""Single authoritative embedding text-builder version."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.errors import UnprocessableError
from app.modules.embeddings.constants import TEXT_VERSION_V1


def resolved_text_version() -> str:
    """Return the builder version. Reject a configured value that does not match it."""
    configured = (get_settings().embedding_text_version or TEXT_VERSION_V1).strip()
    if configured != TEXT_VERSION_V1:
        raise UnprocessableError(
            f"EMBEDDING_TEXT_VERSION '{configured}' does not match the text builder "
            f"version '{TEXT_VERSION_V1}'."
        )
    return TEXT_VERSION_V1
