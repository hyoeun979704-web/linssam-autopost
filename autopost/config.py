"""Load config.yaml and resolve the working folders."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "assets" / "fonts" / "DoHyeon-Regular.ttf"

INBOX_SHORTS = "쇼츠_입문"
INBOX_LONG = "롱폼_라인댄스"
INBOX_CLASS = "수업영상"
PROMO = "홍보문구"
DONE = "완료"
REVIEW = "확인필요"
WORK = ".작업중"


@dataclass
class Folders:
    base: Path

    @property
    def shorts(self) -> Path:
        return self.base / INBOX_SHORTS

    @property
    def long(self) -> Path:
        return self.base / INBOX_LONG

    @property
    def classes(self) -> Path:
        return self.base / INBOX_CLASS

    @property
    def promo(self) -> Path:
        return self.base / PROMO

    @property
    def done(self) -> Path:
        return self.base / DONE

    @property
    def review(self) -> Path:
        return self.base / REVIEW

    @property
    def work(self) -> Path:
        return self.base / WORK

    def ensure(self) -> None:
        for p in (self.shorts, self.long, self.classes, self.promo, self.done, self.review, self.work):
            p.mkdir(parents=True, exist_ok=True)


def load(path: str | os.PathLike | None = None) -> dict:
    p = Path(path) if path else ROOT / "config.yaml"
    if not p.exists():
        raise SystemExit(f"설정 파일이 없습니다: {p}\nconfig.example.yaml 을 config.yaml 로 복사해 채워 주세요.")
    with open(p, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["base_dir"] = str(Path(os.path.expanduser(cfg["base_dir"])))
    cfg["chrome_profile_dir"] = str(Path(os.path.expanduser(cfg.get("chrome_profile_dir", "~/.linssam-autopost/chrome-profile"))))
    return cfg


def folders(cfg: dict) -> Folders:
    return Folders(Path(cfg["base_dir"]))
