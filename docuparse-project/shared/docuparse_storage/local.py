from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from .keys import StoredObject


class LocalStorage:
    """Local filesystem storage with S3-like object keys and local:// URIs."""

    scheme = "local"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def put_bytes(self, key: str, content: bytes) -> StoredObject:
        self._validate_key(key)
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return StoredObject(
            uri=f"{self.scheme}://{key}",
            key=key,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    def get_bytes(self, uri_or_key: str) -> bytes:
        return self._path_for(uri_or_key).read_bytes()

    def delete(self, uri_or_key: str) -> None:
        self._path_for(uri_or_key).unlink(missing_ok=True)

    def clear(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)

    def _path_for(self, uri_or_key: str) -> Path:
        key = uri_or_key.removeprefix(f"{self.scheme}://")
        self._validate_key(key)
        return self.root / key

    @staticmethod
    def _validate_key(key: str) -> None:
        path = Path(key)
        if path.is_absolute() or ".." in path.parts or not key.strip():
            raise ValueError(f"Invalid storage key: {key!r}")
