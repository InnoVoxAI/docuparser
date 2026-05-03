from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LocalJsonlEventBus:
    """Small test adapter that mimics append-only event streams on disk."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, stream: str, event: dict[str, Any]) -> int:
        path = self._stream_path(stream)
        next_offset = self._count(path)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, separators=(",", ":"), default=str))
            file.write("\n")
        return next_offset

    def consume(self, stream: str, offset: int = 0) -> list[dict[str, Any]]:
        path = self._stream_path(stream)
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines()[offset:]:
            if line.strip():
                events.append(json.loads(line))
        return events

    def _stream_path(self, stream: str) -> Path:
        if "/" in stream or ".." in stream or not stream.strip():
            raise ValueError(f"Invalid stream name: {stream!r}")
        return self.root / f"{stream}.jsonl"

    @staticmethod
    def _count(path: Path) -> int:
        if not path.exists():
            return 0
        return len(path.read_text(encoding="utf-8").splitlines())
