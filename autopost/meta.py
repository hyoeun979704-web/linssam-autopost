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


def parse_class_name(stem: str) -> tuple[str, str, str]:
    """"롯데마트 성정점_토요오전반_Hound Dog Cha" -> (center, group, song). Missing parts are ''."""
    parts = [p.strip() for p in re.split(r"[_|]", stem) if p.strip()]
    parts += [""] * (3 - len(parts))
    if len(parts) > 3:
        parts = [parts[0], parts[1], " ".join(parts[2:])]
    return parts[0], parts[1], parts[2]


def class_meta(video: Path, cfg: dict) -> dict:
    """Class / recital footage: proof of teaching for culture-center managers."""
    info, extra = read_sidecar(video)
    center, group, song = parse_class_name(video.stem)
    head = " · ".join(x for x in [center, group] if x)
    title = info.get("title") or " | ".join(x for x in [song, f"{head} 수업" if head else "수업 영상", "천안·아산 셔플&라인댄스 강사"] if x)
    lines = [f"☘️ {head} {song}".strip() + " — 실제 수업 영상입니다."]
    if cfg.get("booking_line"):
        lines.append(cfg["booking_line"])
    lines.append("")
    lines += cfg.get("profile_lines", [])
    lines += extra
    lines += ["", cfg.get("hashtags_class", cfg.get("hashtags_line", ""))]
    desc = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return {"title": title[:100], "description": desc, "band": head or song, "center": center}


def promo_text(meta_: dict, kind: str, cfg: dict, url: str = "") -> str:
    """Ready-to-paste text for Daangn group / Naver blog after an upload."""
    link = url or "(업로드 후 영상 주소)"
    if kind == "class":
        body = [f"오늘 {meta_.get('band', '')} 수업 모습이에요 💗", "", f"🎬 {link}", "",
                "출강 문의 · 수업 문의 모두 카카오톡 채널로 편하게 연락 주세요 😊"]
    else:
        body = [meta_["title"].split(" | ")[0], "", "처음이셔도 천천히 따라오시면 돼요~ 영상 보고 같이 연습해요 💗", "",
                f"🎬 {link}", ""]
        body += cfg.get("info_lines", [])
    if cfg.get("contact_line"):
        body += ["", cfg["contact_line"]]
    return "\n".join(body).strip() + "\n"
