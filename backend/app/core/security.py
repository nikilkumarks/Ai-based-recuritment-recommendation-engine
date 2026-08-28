"""Shared security helpers used outside the identity module.

Password hashing and JWT issuance live in `app.modules.identity`.
This module keeps import-stable helpers for hashing refresh/CSRF tokens.
"""

from __future__ import annotations

import hashlib


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
