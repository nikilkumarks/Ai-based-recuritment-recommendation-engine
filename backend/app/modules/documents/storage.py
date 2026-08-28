"""Blob storage behind an interface so S3 can replace the local disk later."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.modules.documents.constants import STORAGE_KEY_PATTERN, STORAGE_PREFIX


class BlobStore(Protocol):
    def put(self, key: str, data: bytes) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resume_storage_key(digest: str) -> str:
    return f"{STORAGE_PREFIX}/{digest}"


def _assert_safe_key(key: str) -> None:
    if not re.fullmatch(STORAGE_KEY_PATTERN, key):
        raise ValueError("Invalid storage key.")


class LocalBlobStore:
    """Content-addressed files under BLOB_ROOT. Keys are resumes/<sha256> only."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or get_settings().blob_root).resolve()

    def _path(self, key: str) -> Path:
        _assert_safe_key(key)
        path = (self.root / key).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Invalid storage key.") from exc
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()


def get_blob_store() -> BlobStore:
    return LocalBlobStore()
