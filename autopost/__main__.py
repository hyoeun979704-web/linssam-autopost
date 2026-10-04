"""Command line.

python -m autopost login      # (browser 방식일 때만) 크롬에서 채널 계정으로 직접 로그인
python -m autopost tick       # 새 영상 편집 + 시간이 된 영상 업로드 (스케줄러가 30분마다 실행)
python -m autopost edit FILE  # 한 파일만 편집해서 결과 확인 (업로드 안 함)
python -m autopost status     # 대기열 보기
python -m autopost jobs       # 천안·아산 강사 모집 공고 지금 확인 (tick 이 하루 한 번 자동 실행)
"""
from __future__ import annotations

import datetime as dt
import shutil
import sys
import traceback
from pathlib import Path

from . import config as C
from . import edit, jobs, meta, queue

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
LOG = Path.home() / ".linssam-autopost" / "log.txt"


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def unique_dest(folder: Path, name: str) -> Path:
    """Never overwrite: 'a.mp4' -> 'a (2).mp4' if taken."""
    dest = folder / name
    n = 2
    while dest.exists():
        dest = folder / f"{Path(name).stem} ({n}){Path(name).suffix}"
        n += 1
    return dest


def move(src: Path, folder: Path) -> Path:
    dest = unique_dest(folder, src.name)
    shutil.move(str(src), dest)
    return dest


class RunLock:
    """One tick at a time (scheduler + manual run must not overlap)."""

    def __init__(self) -> None:
        self.path = Path.home() / ".linssam-autopost" / "tick.lock"
        self.f = None

    def __enter__(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.path, "a+")
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def __exit__(self, *a) -> None:
        if self.f:
            self.f.close()


def stable(p: Path, wait: float = 3.0) -> bool:
    """Skip files that are still being copied by Google Drive."""
    import time
    a = p.stat().st_size
    time.sleep(wait)
    return a > 0 and a == p.stat().st_size


def process_new(cfg: dict) -> None:
    f = C.folders(cfg)
    f.ensure()
    for kind, inbox in (("shorts", f.shorts), ("long", f.long), ("class", f.classes)):
        for src in sorted(inbox.iterdir()):
            if src.suffix.lower() not in VIDEO_EXT or src.name.startswith("."):
                continue
            try:
                if not stable(src):
                    continue
            except OSError:
                continue  # Drive moved or deleted it while we looked
            key = f"{cfg.get('channel_name', '')}:{kind}:{src.stem}:{src.stat().st_size}"
            if any(i["key"] == key for i in queue.items()):
                continue
            log(f"편집 시작: {src.name}")
            stem = f"{src.stem}_{dt.datetime.now():%Y%m%d%H%M%S}"
            try:
                m = {"shorts": meta.shorts_meta, "long": meta.long_meta, "class": meta.class_meta}[kind](src, cfg)
                render_kind, opts = kind, dict(cfg.get("edit", {}))
                if kind == "class":
                    # class footage keeps its own orientation; no beat counts, no tracking needed
                    pr = edit.probe(src)
                    render_kind = "shorts" if pr.height > pr.width else "long"
                    opts["count_captions"] = False
                    opts["max_shorts_sec"] = 10 ** 6
                res = edit.render(src, f.work, kind=render_kind, title=m["band"],
                                  class_line=cfg.get("booking_end_line", "") if kind == "class" else cfg.get("class_line", ""),
                                  opts=opts, out_stem=stem)
            except Exception as e:  # noqa: BLE001
                log(f"편집 실패: {src.name} — {e}")
                moved = move(src, f.review)
                unique_dest(f.review, f"{moved.stem}_문제.txt").write_text(f"편집 실패: {e}", encoding="utf-8")
                continue
            if res.problems:
                log(f"확인필요: {src.name} — {' / '.join(res.problems)}")
                moved = move(src, f.review)
                move(res.video, f.review)
                unique_dest(f.review, f"{moved.stem}_문제.txt").write_text("\n".join(res.problems), encoding="utf-8")
                continue
            if res.warnings:
                log(f"참고: {src.name} — {' / '.join(res.warnings)}")
            entry = queue.add({"key": key, "kind": kind, "channel": cfg.get("channel_name", ""), "band": m["band"], "source": src.name, "video": str(res.video),
                               "thumbnail": str(res.thumbnail), "title": m["title"], "description": m["description"]}, cfg)
            move(src, f.done)
            log(f"대기열 추가: {m['title']} → {entry['slot']}")


def upload_due(cfg: dict) -> None:
    if cfg.get("upload_method", "aside") == "aside":
        from . import upload_aside as uploader
    else:
        from . import upload_browser as uploader
    for item in queue.items():
        if item["status"] == "uploading":
            started = dt.datetime.fromisoformat(item.get("started_at", item["slot"]))
            if dt.datetime.now() - started > dt.timedelta(hours=2):
                queue.update(item["key"], status="check", error="업로드 도중 멈췄습니다. 스튜디오에서 올라갔는지 확인해 주세요.")
                log(f"확인필요(업로드 중단): {item['title']}")
    for i in queue.reslot_overdue(cfg, channel=cfg.get("channel_name", "")):
        log(f"밀린 영상 시간 다시 잡음: {i['title']} → {i['slot']}")
    # at most one upload per kind per run, so a backlog never floods the channel
    seen_kinds = set()
    for item in queue.due(channel=cfg.get("channel_name", "")):
        if item["kind"] in seen_kinds:
            continue
        seen_kinds.add(item["kind"])
        attempts = item.get("attempts", 0) + 1
        queue.update(item["key"], status="uploading", attempts=attempts, started_at=dt.datetime.now().isoformat())
        log(f"업로드 시작({attempts}회째): {item['title']}")
        try:
            url = uploader.upload(cfg, Path(item["video"]), item["title"], item["description"],
                                        Path(item["thumbnail"]) if item["kind"] == "long" else None)
            queue.update(item["key"], status="uploaded", url=url, uploaded_at=dt.datetime.now().isoformat())
            log(f"업로드 완료: {item['title']} {url}")
            try:
                f = C.folders(cfg)
                text = meta.promo_text({"title": item["title"], "band": item.get("band", "")}, item["kind"], cfg, url)
                name = f"{dt.date.today():%m%d} {Path(item['source']).stem} 당근·블로그용.txt"
                unique_dest(f.promo, name).write_text(text, encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                log(f"홍보문구 저장 실패: {e}")
        except Exception as e:  # noqa: BLE001
            safe = getattr(e, "retry_safe", False)  # unknown errors: a person checks before retrying
            queue.update(item["key"], status="failed" if safe else "check", error=str(e),
                         failed_at=dt.datetime.now().isoformat())
            log(f"업로드 실패: {item['title']} — {e}")
            notify("린쌤 자동업로드 실패", str(e)[:120])


def notify(title: str, body: str) -> None:
    import platform
    import subprocess
    if platform.system() == "Darwin":
        subprocess.run(["osascript", "-e", f'display notification "{body}" with title "{title}"'], check=False)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    cfg = C.load()
    if cmd == "login":
        from . import upload_browser
        upload_browser.login(cfg)
    elif cmd == "tick":
        with RunLock() as got:
            if not got:
                print("이미 실행 중입니다.")
                return 0
            code = 0
            try:
                process_new(cfg)
            except Exception:  # noqa: BLE001
                log("편집 단계 오류:\n" + traceback.format_exc())
                code = 1
            try:
                if cfg.get("upload_method", "aside") in ("aside", "browser"):
                    upload_due(cfg)
            except Exception:  # noqa: BLE001
                log("업로드 단계 오류:\n" + traceback.format_exc())
                code = 1
            try:
                if cfg.get("job_alerts", True) and jobs.due():
                    new = jobs.run(C.folders(cfg).base / "강사모집공고.md")
                    hot = [n for n in new if n["hot"]]
                    log(f"강사 모집 공고 확인: 새 공고 {len(new)}건 (관련 {len(hot)}건)")
                    if hot:
                        notify("강사 모집 공고", " / ".join(n["title"][:30] for n in hot[:3]))
            except Exception:  # noqa: BLE001
                log("공고 확인 오류:\n" + traceback.format_exc())
            return code
    elif cmd == "edit":
        src = Path(argv[1])
        kind = argv[2] if len(argv) > 2 else ("long" if C.INBOX_LONG in str(src) else "class" if C.INBOX_CLASS in str(src) else "shorts")
        m = {"shorts": meta.shorts_meta, "long": meta.long_meta, "class": meta.class_meta}[kind](src, cfg)
        if kind == "class":
            pr = edit.probe(src)
            kind = "shorts" if pr.height > pr.width else "long"
        res = edit.render(src, src.parent / "편집결과", kind=kind, title=m["band"],
                          class_line=cfg.get("class_line", ""), opts=cfg.get("edit", {}),
                          out_stem=f"{src.stem}_{dt.datetime.now():%Y%m%d%H%M%S}")
        print("영상:", res.video, f"({res.duration:.1f}초)")
        print("썸네일:", res.thumbnail)
        print("제목:", m["title"])
        print("설명:\n" + m["description"])
        print("멈출 문제:", " / ".join(res.problems) or "없음")
        print("참고:", " / ".join(res.warnings) or "없음")
    elif cmd == "jobs":
        out = C.folders(cfg).base / "강사모집공고.md"
        new = jobs.run(out)
        print(f"새 공고 {len(new)}건 → {out}")
        for n in new:
            print(("⭐ " if n["hot"] else "   ") + n["title"])
    elif cmd == "status":
        for i in queue.items():
            print(f"{i['status']:9} {i['slot'][:16]}  {i['title']}  {i.get('url', '')}{i.get('error', '')}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
