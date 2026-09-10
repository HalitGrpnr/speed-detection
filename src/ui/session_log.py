"""Oturum logu — her job için session_log.jsonl dosyasına olay kaydeder.

İki yere yazılır:
  1. Temp job dizini (job_dir/session_log.jsonl) — mevcut pipeline akışıyla uyumlu
  2. Kalıcı dizin (data/sessions/{job_id}/session_log.jsonl) — sunucu yeniden
     başlasa bile erişilebilir, Claude doğrudan okuyabilir
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# Proje kökü: src/ui/session_log.py → ../../.. → proje kökü
SESSIONS_DIR = Path(__file__).parent.parent.parent / "data" / "sessions"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append(job_dir: Path, event: str, *, _job_id: str | None = None, **kwargs) -> None:
    """İki yere log satırı ekler: temp job_dir ve kalıcı data/sessions/{_job_id}/.

    _job_id: kalıcı dizin için; log satırına "job_id" olarak da eklenir.
    """
    entry: dict = {"ts": _now(), "event": event}
    if _job_id:
        entry["job_id"] = _job_id
    entry.update({k: v for k, v in kwargs.items() if v is not None})
    line = json.dumps(entry, ensure_ascii=False) + "\n"

    # 1. Temp dizin (mevcut pipeline akışı)
    with open(job_dir / "session_log.jsonl", "a", encoding="utf-8") as f:
        f.write(line)

    # 2. Kalıcı dizin
    if _job_id:
        persistent = SESSIONS_DIR / _job_id
        persistent.mkdir(parents=True, exist_ok=True)
        with open(persistent / "session_log.jsonl", "a", encoding="utf-8") as f:
            f.write(line)


def read(job_dir: Path) -> list[dict]:
    """Temp dizinden log satırlarını okur (API endpoint için)."""
    return _parse(job_dir / "session_log.jsonl")


def read_persistent(job_id: str) -> list[dict]:
    """Kalıcı dizinden log satırlarını okur."""
    return _parse(SESSIONS_DIR / job_id / "session_log.jsonl")


def list_recent(n: int = 20) -> list[dict]:
    """En son n oturumu döndürür (job_id + ilk/son olay + zaman damgası)."""
    if not SESSIONS_DIR.exists():
        return []
    sessions = []
    for log_path in sorted(SESSIONS_DIR.glob("*/session_log.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]:
        entries = _parse(log_path)
        if entries:
            sessions.append({
                "job_id": log_path.parent.name,
                "first_event": entries[0].get("event"),
                "last_event": entries[-1].get("event"),
                "ts_start": entries[0].get("ts"),
                "ts_end": entries[-1].get("ts"),
                "event_count": len(entries),
            })
    return sessions


def _parse(path: Path) -> list[dict]:
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
