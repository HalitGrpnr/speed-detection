"""Oturum logu — her job için session_log.jsonl dosyasına olay kaydeder."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append(job_dir: Path, event: str, **kwargs) -> None:
    """job_dir/session_log.jsonl dosyasına bir satır ekler."""
    entry = {"ts": _now(), "event": event, **{k: v for k, v in kwargs.items() if v is not None}}
    with open(job_dir / "session_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read(job_dir: Path) -> list[dict]:
    path = job_dir / "session_log.jsonl"
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries
