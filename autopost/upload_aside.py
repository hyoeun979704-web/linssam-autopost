"""Upload through YouTube Studio in the owner's Aside browser (`aside repl`).

Aside keeps the owner's Google login. This script never logs in, logs out or switches
accounts. It checks the channel name shown in Studio's left menu and stops on any mismatch.

`aside repl` calls are limited to about 120 seconds each, so the upload runs in phases:
  1. open Studio, check the channel, pick the file, fill title/description/options
  2. (repeated) find that upload tab again and wait for the Done button, then publish
The browser keeps uploading between calls.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import time
from pathlib import Path

CHANNEL_JS = r"""
async function channelNames(pg) {
  return await pg.evaluate(`[...document.querySelectorAll('#entity-name, ytcp-navigation-drawer #entity-name, .entity-name, #channel-title')]
    .map(e => (e.innerText || '').trim()).filter(Boolean)`);
}
"""

PHASE1 = CHANNEL_JS + r"""
const A = __ARGS__;
const say = (o) => console.log('@@RESULT@@' + JSON.stringify(o));
let pg;
try {
  pg = await openTab('https://studio.youtube.com');
  await sleep(8000);
  if (pg.url().includes('accounts.google.com')) {
    say({ok:false, fatal:true, error:'Aside 브라우저에서 유튜브 로그인이 풀렸습니다. 직접 로그인해 주세요.'});
    await closeTab(pg);
  } else {
    const names = await channelNames(pg);
    if (!names.includes(A.channel)) {
      say({ok:false, fatal:true, error:`스튜디오 채널명이 '${A.channel}' 와 다릅니다(보이는 이름: ${names.join(', ') || '찾지 못함'}). 업로드를 멈췄습니다.`});
      await closeTab(pg);
    } else {
      await pg.goto('https://www.youtube.com/upload');
      await sleep(6000);
      await pg.locator('input[type=file]').first().setInputFiles(A.video);
      await pg.locator('#title-textarea #textbox').waitFor({timeout:60000});
      await sleep(2500);
      for (const [sel, text] of [['#title-textarea #textbox', A.title], ['#description-textarea #textbox', A.description]]) {
        await pg.locator(sel).first().click();
        await pg.keyboard.press(A.mac ? 'Meta+A' : 'Control+A');
        await pg.keyboard.press('Backspace');
        await pg.keyboard.insertText(text);
        await sleep(500);
      }
      if (A.thumbnail) {
        const ti = pg.locator('#file-loader input[type=file], input#file-loader');
        if (await ti.count()) { await ti.first().setInputFiles(A.thumbnail); await sleep(3000); }
      }
      await pg.locator('tp-yt-paper-radio-button[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]').first().click();
      for (let i = 0; i < 3; i++) { await pg.locator('#next-button').click(); await sleep(1500); }
      await pg.locator(`tp-yt-paper-radio-button[name=${A.public ? 'PUBLIC' : 'PRIVATE'}]`).first().click();
      let url = '';
      try { url = await pg.locator('a.style-scope.ytcp-video-info, .video-url-fadeable a').first().getAttribute('href'); } catch (e) {}
      say({ok:true, phase:1, url, tabUrl: pg.url()});
    }
  }
} catch (e) { say({ok:false, error:String(e).slice(0,300)}); try { if (pg) await closeTab(pg); } catch (e2) {} }
"""

PHASE2 = r"""
const A = __ARGS__;
const say = (o) => console.log('@@RESULT@@' + JSON.stringify(o));
try {
  const tabs = await listBrowserTabs();
  const t = tabs.find(x => (x.url || '').includes('studio.youtube.com') && (x.url || '').includes(A.tabHint));
  if (!t) { say({ok:false, error:'업로드 창을 다시 찾지 못했습니다.'}); }
  else {
    const pg = await attachBrowserTab(t.targetId);
    let done = false;
    for (let i = 0; i < 30; i++) {
      if (await pg.locator('#done-button').isEnabled()) { done = true; break; }
      await sleep(3000);
    }
    if (!done) { say({ok:true, phase:2, waiting:true}); }
    else {
      await pg.locator('#done-button').click();
      await sleep(5000);
      say({ok:true, phase:2, waiting:false});
      try { await closeTab(pg); } catch (e) {}
    }
  }
} catch (e) { say({ok:false, error:String(e).slice(0,300)}); }
"""


def _aside() -> str:
    return shutil.which("aside") or str(Path.home() / ".local" / "bin" / "aside")


def _call(cfg: dict, js: str, args: dict) -> dict:
    cmd = [_aside(), "repl"]
    if cfg.get("aside_account"):
        cmd += ["--account", str(cfg["aside_account"])]
    cmd.append(js.replace("__ARGS__", json.dumps(args, ensure_ascii=False)))
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        if "@@RESULT@@" in line:
            return json.loads(line.split("@@RESULT@@", 1)[1])
    return {"ok": False, "error": "Aside 응답이 없습니다: " + out[-300:]}


def upload(cfg: dict, video: Path, title: str, description: str, thumbnail: Path | None = None,
           public: bool = True, max_wait_min: int = 40) -> str:
    args = {"video": str(video.resolve()), "title": title, "description": description,
            "thumbnail": str(thumbnail.resolve()) if thumbnail else "", "public": public,
            "channel": cfg.get("channel_name", "").strip(), "mac": platform.system() == "Darwin"}
    r = _call(cfg, PHASE1, args)
    if not r.get("ok"):
        raise RuntimeError(r.get("error", "알 수 없는 오류"))
    url = r.get("url", "")
    hint = "/upload" if "/upload" in r.get("tabUrl", "") else "studio.youtube.com"
    if "/video/" in r.get("tabUrl", ""):
        hint = r["tabUrl"].split("/video/")[1].split("/")[0]
    deadline = time.time() + max_wait_min * 60
    while time.time() < deadline:
        r = _call(cfg, PHASE2, {"tabHint": hint})
        if not r.get("ok"):
            raise RuntimeError(r.get("error", "알 수 없는 오류"))
        if not r.get("waiting"):
            return url
        time.sleep(5)
    raise RuntimeError(f"{max_wait_min}분 안에 업로드 처리가 끝나지 않았습니다.")
