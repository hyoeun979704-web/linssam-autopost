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
    tmp = STATE.with_suffix(".tmp")
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


def add(entry: dict, cfg: dict) -> dict:
    q = _load()
    taken = {i["slot"] for i in q if i["status"] in ("waiting", "uploaded") and i["kind"] == entry["kind"]}
    entry["slot"] = next_slot(entry["kind"], cfg, taken).isoformat()
    entry["status"] = "waiting"
    q.append(entry)
    _save(q)
    return entry


def due(now: dt.datetime | None = None) -> list[dict]:
    now = now or dt.datetime.now()
    return [i for i in _load() if i["status"] == "waiting" and dt.datetime.fromisoformat(i["slot"]) <= now]


def update(key: str, **fields) -> None:
    q = _load()
    for i in q:
        if i["key"] == key:
            i.update(fields)
    _save(q)
