"""A small JSON queue: edited videos wait here for their upload slot."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

STATE = Path.home() / ".linssam-autopost" / "queue.json"


def _load() -> list[dict]:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return []


def _save(items: list[dict]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    import os
    tmp = STATE.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE)


def items() -> list[dict]:
    return _load()


def _hhmm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


def next_slot(kind: str, cfg: dict, taken: set[str], now: dt.datetime | None = None) -> dt.datetime:
    now = now or dt.datetime.now()
    sch = cfg["schedule"]["shorts" if kind == "shorts" else "long"]
    h, m = _hhmm(sch["time"])
    day = now.date()
    for _ in range(400):
        cand = dt.datetime.combine(day, dt.time(h, m))
        if kind == "shorts":
            ok = day.weekday() in sch["weekdays"]
        else:
            ok = day.weekday() == sch["monthly_weekday"] and day.day <= 7
        if ok and cand > now and cand.isoformat() not in taken:
            return cand
        day += dt.timedelta(days=1)
    raise RuntimeError("업로드 시간을 찾지 못했습니다. schedule 설정을 확인하세요.")


def _taken(q: list[dict], kind: str, channel: str) -> set[str]:
    return {i["slot"] for i in q if i["status"] in ("waiting", "uploading", "uploaded", "failed")
            and i["kind"] == kind and i.get("channel", "") == channel}


def reslot_overdue(cfg: dict, grace_hours: float = 6, now: dt.datetime | None = None) -> list[dict]:
    """The computer was off: move long-overdue waiting items to the next free slots instead of
    publishing them all at once."""
    now = now or dt.datetime.now()
    q = _load()
    moved = []
    for i in sorted(q, key=lambda x: x["slot"]):
        if i["status"] == "waiting" and dt.datetime.fromisoformat(i["slot"]) < now - dt.timedelta(hours=grace_hours):
            i["slot"] = next_slot(i["kind"], cfg, _taken(q, i["kind"], i.get("channel", "")), now).isoformat()
            moved.append(i)
    if moved:
        _save(q)
    return moved


def add(entry: dict, cfg: dict) -> dict:
    q = _load()
    taken = _taken(q, entry["kind"], entry.get("channel", ""))
    entry["slot"] = next_slot(entry["kind"], cfg, taken).isoformat()
    entry["status"] = "waiting"
    q.append(entry)
    _save(q)
    return entry


MAX_ATTEMPTS = 3
RETRY_AFTER = dt.timedelta(minutes=30)


def due(now: dt.datetime | None = None, channel: str | None = None) -> list[dict]:
    """Waiting items whose slot has come, plus failed ones that may be retried."""
    now = now or dt.datetime.now()
    out = []
    for i in _load():
        if dt.datetime.fromisoformat(i["slot"]) > now:
            continue
        if channel is not None and i.get("channel", "") != channel:
            continue
        if i["status"] == "waiting":
            out.append(i)
        elif i["status"] == "failed" and i.get("attempts", 0) < MAX_ATTEMPTS:
            last = dt.datetime.fromisoformat(i.get("failed_at", i["slot"]))
            if now - last >= RETRY_AFTER:
                out.append(i)
    return sorted(out, key=lambda x: x["slot"])


def update(key: str, **fields) -> None:
    q = _load()
    for i in q:
        if i["key"] == key:
            i.update(fields)
    _save(q)
