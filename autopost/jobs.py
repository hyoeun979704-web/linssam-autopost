"""Instructor-call alerts: read the public notice boards of Cheonan and Asan once a day,
keep every notice whose title asks for an instructor (강사 모집), and write them into one
file in the Drive folder (`강사모집공고.md`) so it can be read on the phone.

Only public list pages are read (plain HTTP GET, a few pages per board, once a day).
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (linssam-autopost; instructor-call alerts)"
STATE = Path.home() / ".linssam-autopost" / "jobs.json"

CHEONAN = "https://www.cheonan.go.kr"
ASAN = "https://asan.go.kr"

# (name, list url with {page}, regex -> (href, title), base, pages)
SOURCES = [
    ("천안시 공고·고시", CHEONAN + "/prog/saeolGosi/GOSI/kor/sub02_02_01/list.do?pageIndex={page}",
     r'href="(/prog/saeolGosi/GOSI/kor/sub02_02_01/view\.do\?notAncmtMgtNo=\d+)"[^>]*>(.*?)</a>', CHEONAN, 8),
    ("천안시 채용공고", CHEONAN + "/prog/saeolGosi/GOSI_05/kor/sub02_02_02_01/list.do?pageIndex={page}",
     r'href="(/prog/saeolGosi/GOSI_05/kor/sub02_02_02_01/view\.do\?notAncmtMgtNo=\d+)"[^>]*>(.*?)</a>', CHEONAN, 3),
    ("천안시 평생학습 소식", CHEONAN + "/bbs/BBSMSTR_000000000104/list.do?pageIndex={page}",
     r"fn_search_detail\('([^']+)'\).*?board__subject-text\">(.*?)</strong>",
     CHEONAN + "/bbs/BBSMSTR_000000000104/view.do?nttId=", 3),
    ("천안시 주민자치 소식", CHEONAN + "/bbs/BBSMSTR_000000000245/list.do?pageIndex={page}",
     r"fn_search_detail\('([^']+)'\).*?board__subject-text\">(.*?)</strong>",
     CHEONAN + "/bbs/BBSMSTR_000000000245/view.do?nttId=", 3),
    ("아산시 채용·시험공고", ASAN + "/main/cms/?no=140&tb_nm=exam&m_mode=list&PageNo={page}",
     r"href='(\?tb_nm=exam&m_mode=view&pds_no=\d+)[^']*'[^>]*>(.*?)</a>", ASAN + "/main/cms/", 5),
]

MUST = re.compile(r"강사")
SKIP = re.compile(r"합격자|결과|면접|서류전형|최종|취소|변경|정정|모집완료|마감")
HOT = re.compile(r"라인|셔플|댄스|에어로빅|줌바|체조|건강|운동|생활체육|주민자치|평생|문화|프로그램")


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="ignore")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def scan() -> tuple[list[dict], list[str]]:
    found, errors = [], []
    for name, tmpl, rx, base, pages in SOURCES:
        for page in range(1, pages + 1):
            try:
                s = _get(tmpl.format(page=page))
            except Exception as e:  # noqa: BLE001
                errors.append(f"{name} {page}쪽: {e}")
                break
            for href, raw in re.findall(rx, s, re.S):
                title = re.sub(r"^D-\d+\s*", "", _clean(raw))
                if MUST.search(title) and not SKIP.search(title):
                    url = base + href
                    found.append({"source": name, "title": title, "url": url, "hot": bool(HOT.search(title))})
    uniq = {f["url"]: f for f in found}
    return list(uniq.values()), errors


def _load() -> dict:
    try:
        if STATE.exists():
            return json.loads(STATE.read_text(encoding="utf-8"))
    except ValueError:
        pass  # a broken state file starts over instead of stopping the alerts
    return {"seen": {}, "last_run": ""}


def _save(st: dict) -> None:
    import os
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(STATE)


def due(hours: float = 20) -> bool:
    st = _load()
    if not st.get("last_run"):
        return True
    return dt.datetime.now() - dt.datetime.fromisoformat(st["last_run"]) > dt.timedelta(hours=hours)


def run(out_file: Path) -> list[dict]:
    """Scan, remember, rewrite the Drive file. Returns the notices that are new today."""
    st = _load()
    found, errors = scan()
    today = dt.date.today().isoformat()
    new = []
    for f in found:
        if f["url"] not in st["seen"]:
            st["seen"][f["url"]] = {**f, "first_seen": today}
            new.append(f)
    items = sorted(st["seen"].values(), key=lambda x: (x["first_seen"], x["hot"]), reverse=True)[:60]
    lines = ["# 강사 모집 공고 (천안·아산)", "",
             f"마지막 확인: {dt.datetime.now():%Y-%m-%d %H:%M} · 매일 한 번 자동으로 갱신됩니다.",
             "⭐ = 댄스·운동·주민자치·평생학습 관련으로 보이는 공고", ""]
    for i in items:
        star = "⭐ " if i["hot"] else ""
        mark = " 🆕" if i["first_seen"] == today else ""
        lines.append(f"- {star}{i['title']}{mark}  \n  {i['source']} · {i['first_seen']} · {i['url']}")
    if errors:
        lines += ["", "읽지 못한 게시판: " + " / ".join(errors)]
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    st["last_run"] = dt.datetime.now().isoformat()  # only after the Drive file is written
    _save(st)
    return new
