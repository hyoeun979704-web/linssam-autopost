"""Upload through YouTube Studio in a real Chrome window.

Why a browser and not the API: videos uploaded through the YouTube Data API from an
unverified Google Cloud project are locked to private until the project passes Google's
audit (videos.insert docs). Studio in a normal Chrome has no such lock.

Login is done once by a person (`python -m autopost login`). This script never types a
password; it reuses the saved Chrome profile.
"""
from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path

STUDIO = "https://studio.youtube.com"


def chrome_path() -> str:
    cands = []
    if platform.system() == "Darwin":
        cands = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    elif platform.system() == "Windows":
        for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")):
            cands.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    else:
        cands = [shutil.which("google-chrome") or "", shutil.which("chromium") or ""]
    for c in cands:
        if c and Path(c).exists():
            return c
    raise SystemExit("크롬을 찾지 못했습니다. Google Chrome 을 설치해 주세요.")


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def open_chrome(profile_dir: str, port: int, url: str = STUDIO, debug: bool = True) -> subprocess.Popen | None:
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    if debug and _port_open(port):
        return None
    args = [chrome_path(), f"--user-data-dir={profile_dir}", "--no-first-run", "--no-default-browser-check"]
    if debug:
        args.append(f"--remote-debugging-port={port}")
    args.append(url)
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if debug:
        for _ in range(60):
            if _port_open(port):
                break
            time.sleep(0.5)
    return proc


def login(cfg: dict) -> None:
    """Open Chrome with the dedicated profile so the owner can sign in by hand."""
    print("크롬 창이 열리면 유튜브 채널 계정으로 직접 로그인하고, 스튜디오 화면이 보이면 창을 닫아 주세요.")
    proc = open_chrome(cfg["chrome_profile_dir"], cfg["chrome_debug_port"], STUDIO, debug=False)
    if proc:
        proc.wait()
    print("로그인 정보가 저장되었습니다.")


def _set_text(page, selector: str, text: str) -> None:
    box = page.locator(selector).first
    box.click()
    page.keyboard.press("Meta+A" if platform.system() == "Darwin" else "Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.insert_text(text)


def upload(cfg: dict, video: Path, title: str, description: str, thumbnail: Path | None = None,
           public: bool = True, timeout_min: int = 30) -> str:
    """Upload one video. Returns the video URL. Raises on any mismatch."""
    from playwright.sync_api import sync_playwright

    proc = open_chrome(cfg["chrome_profile_dir"], cfg["chrome_debug_port"])
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{cfg['chrome_debug_port']}")
            ctx = browser.contexts[0]
            page = ctx.new_page()
            page.goto(STUDIO, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            if "accounts.google.com" in page.url:
                raise RuntimeError("로그인이 풀렸습니다. `python -m autopost login` 으로 다시 로그인해 주세요.")

            # Account check: the channel name shown in Studio must match the config.
            want = cfg.get("channel_name", "").strip()
            if want:
                page.locator("#avatar-btn, ytcp-home-button, #entity-name").first.wait_for(timeout=30000)
                body = page.locator("body").inner_text()
                if want not in body:
                    raise RuntimeError(f"스튜디오에 보이는 채널이 '{want}' 가 아닙니다. 업로드를 멈췄습니다.")

            page.goto("https://www.youtube.com/upload", wait_until="domcontentloaded")
            page.locator("input[type=file]").first.set_input_files(str(video))
            page.locator("#title-textarea #textbox").wait_for(timeout=120000)
            page.wait_for_timeout(2500)
            _set_text(page, "#title-textarea #textbox", title)
            _set_text(page, "#description-textarea #textbox", description)

            if thumbnail and thumbnail.exists():
                thumb_input = page.locator("#file-loader input[type=file], input#file-loader")
                if thumb_input.count():
                    thumb_input.first.set_input_files(str(thumbnail))
                    page.wait_for_timeout(3000)

            page.locator("tp-yt-paper-radio-button[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]").first.click()
            for _ in range(3):
                page.locator("#next-button").click()
                page.wait_for_timeout(1500)
            page.locator(f"tp-yt-paper-radio-button[name={'PUBLIC' if public else 'PRIVATE'}]").first.click()

            link = page.locator("a.style-scope.ytcp-video-info, .video-url-fadeable a").first
            url = link.get_attribute("href") or ""

            # wait until the upload finishes processing enough to publish
            deadline = time.time() + timeout_min * 60
            while time.time() < deadline:
                done = page.locator("#done-button")
                if done.is_enabled():
                    break
                page.wait_for_timeout(3000)
            page.locator("#done-button").click()
            page.wait_for_timeout(5000)
            page.close()
            return url
    finally:
        if proc:
            proc.terminate()
