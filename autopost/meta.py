"""Titles and descriptions from the file name and folder.

Shorts file name : "03 T스텝.mp4"     -> "셔플 입문 3/12 · T스텝 · 완전초보 따라하기 | 천안셔플댄스"
Long file name   : "Lucky Lips.mp4"   -> "Lucky Lips · 라인댄스 | 천안라인댄스"
Optional extras  : a .txt file with the same name next to the video. Lines of the form
                   "레벨: Absolute Beginner", "안무: Gary Lafferty", "한글: 럭키 립스",
                   "스텝시트: https://..." are picked up. Anything else is added to the description.
"""
from __future__ import annotations

import re
from pathlib import Path

KEYS = {"레벨": "level", "level": "level", "안무": "choreo", "choreo": "choreo", "한글": "korean",
        "스텝시트": "sheet", "stepsheet": "sheet", "카운트": "count", "count": "count", "월": "wall", "wall": "wall",
        "제목": "title"}


def read_sidecar(video: Path) -> tuple[dict, list[str]]:
    txt = video.with_suffix(".txt")
    info: dict = {}
    extra: list[str] = []
    if txt.exists():
        for line in txt.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*([^:：]+)[:：]\s*(.+)", line)
            key = KEYS.get(m.group(1).strip().lower()) if m else None
            if key:
                info[key] = m.group(2).strip()
            elif line.strip():
                extra.append(line.strip())
    return info, extra


def parse_shorts_name(stem: str) -> tuple[int | None, str]:
    m = re.match(r"\s*(\d{1,2})[\s._-]*(.*)", stem)
    if m:
        return int(m.group(1)), m.group(2).strip() or stem
    return None, stem.strip()


def shorts_meta(video: Path, cfg: dict) -> dict:
    info, extra = read_sidecar(video)
    num, move = parse_shorts_name(video.stem)
    series, total = cfg.get("shorts_series", "셔플 입문"), cfg.get("shorts_total", 12)
    band = f"{series} {num}/{total} · {move}" if num else f"{series} · {move}"
    title = info.get("title") or f"{band} · {cfg.get('shorts_level', '완전초보 따라하기')} | {cfg.get('region_tag', '')}".rstrip(" |")
    # The first two lines show above "더보기": what this is + how to sign up.
    lines = [f"☘️ {series} {total}스텝 {num}번 {move} · 처음이셔도 천천히 따라오시면 돼요~" if num
             else f"☘️ {move} · 처음이셔도 천천히 따라오시면 돼요~"]
    if cfg.get("contact_line"):
        lines.append(cfg["contact_line"])
    lines.append("")
    lines += cfg.get("info_lines", [])
    lines += extra
    lines += ["", cfg.get("hashtags", "")]
    return {"title": title[:100], "description": "\n".join(lines).strip(), "band": band}


def long_meta(video: Path, cfg: dict) -> dict:
    info, extra = read_sidecar(video)
    song = video.stem.strip()
    level = info.get("level", "")
    korean = info.get("korean", "")
    name = f"{song} {korean}".strip() if korean else song
    title = info.get("title") or " · ".join(x for x in [name, f"{level} 라인댄스" if level else "라인댄스"] if x) + " | 천안·아산"
    lines = [f"☘️ {song}" + (f" · {level}" if level else "")]
    if cfg.get("contact_line"):
        lines.append(cfg["contact_line"])
    lines.append("")
    lines += cfg.get("info_lines_long", [])
    lines.append("")
    for label, key in [("Count", "count"), ("Wall", "wall"), ("Level", "level"), ("Choreo", "choreo")]:
        if info.get(key):
            lines.append(f"{label}: {info[key]}")
    lines.append("")
    if info.get("sheet"):
        lines.append(f"☘️ 스텝순서가 궁금하시다면 아래를 클릭하세요\n{info['sheet']}")
    else:
        q = song.replace(" ", "+")
        lines.append(f"☘️ 스텝시트 찾기: https://www.copperknob.co.uk/search?q={q}")
    lines += extra
    lines += ["", cfg.get("hashtags_line", "")]
    thumb_text = f"{song}" + (f" · {level}" if level else "")
    desc = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return {"title": title[:100], "description": desc, "band": thumb_text}
