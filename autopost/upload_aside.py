"""Upload through YouTube Studio in the owner's Aside browser (`aside repl`).

Aside keeps the owner's Google login. This script never logs in, logs out or switches
accounts; if Studio shows another channel it stops before touching anything.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

JS = r"""
const ARGS = __ARGS__;
const say = (o) => console.log('@@RESULT@@' + JSON.stringify(o));
let pg;
try {
  pg = await openTab('https://studio.youtube.com');
  await sleep(8000);
  if (pg.url().includes('accounts.google.com')) { say({ok:false, error:'Aside 브라우저에서 유튜브 로그인이 풀렸습니다. 직접 로그인해 주세요.'}); }
  else {
    const body = await pg.evaluate('document.body.innerText');
    if (ARGS.channel && !body.includes(ARGS.channel)) {
      say({ok:false, error:`스튜디오에 보이는 채널이 '${ARGS.channel}' 가 아닙니다. 업로드를 멈췄습니다.`});
    } else {
      await pg.goto('https://www.youtube.com/upload');
      await sleep(6000);
      await pg.locator('input[type=file]').first().setInputFiles(ARGS.video);
      await pg.locator('#title-textarea #textbox').waitFor({timeout:120000});
      await sleep(2500);
      for (const [sel, text] of [['#title-textarea #textbox', ARGS.title], ['#description-textarea #textbox', ARGS.description]]) {
        await pg.locator(sel).first().click();
        await pg.keyboard.press(ARGS.mac ? 'Meta+A' : 'Control+A');
        await pg.keyboard.press('Backspace');
        await pg.keyboard.insertText(text);
        await sleep(500);
      }
      if (ARGS.thumbnail) {
        const ti = pg.locator('#file-loader input[type=file], input#file-loader');
        if (await ti.count()) { await ti.first().setInputFiles(ARGS.thumbnail); await sleep(3000); }
      }
      await pg.locator('tp-yt-paper-radio-button[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]').first().click();
      for (let i = 0; i < 3; i++) { await pg.locator('#next-button').click(); await sleep(1500); }
      await pg.locator(`tp-yt-paper-radio-button[name=${ARGS.public ? 'PUBLIC' : 'PRIVATE'}]`).first().click();
      let url = '';
      try { url = await pg.locator('a.style-scope.ytcp-video-info, .video-url-fadeable a').first().getAttribute('href'); } catch (e) {}
      for (let i = 0; i < 24; i++) { if (await pg.locator('#done-button').isEnabled()) break; await sleep(3000); }
      await pg.locator('#done-button').click();
      await sleep(5000);
      say({ok:true, url});
    }
  }
} catch (e) { say({ok:false, error:String(e).slice(0,300)}); }
try { if (pg) await closeTab(pg); } catch (e) {}
"""


def upload(cfg: dict, video: Path, title: str, description: str, thumbnail: Path | None = None,
           public: bool = True) -> str:
    import platform
    aside = shutil.which("aside") or str(Path.home() / ".local" / "bin" / "aside")
    args = {"video": str(video.resolve()), "title": title, "description": description,
            "thumbnail": str(thumbnail.resolve()) if thumbnail else "", "public": public,
            "channel": cfg.get("channel_name", ""), "mac": platform.system() == "Darwin"}
    code = JS.replace("__ARGS__", json.dumps(args, ensure_ascii=False))
    cmd = [aside, "repl"]
    if cfg.get("aside_account"):
        cmd += ["--account", str(cfg["aside_account"])]
    cmd.append(code)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        if "@@RESULT@@" in line:
            res = json.loads(line.split("@@RESULT@@", 1)[1])
            if res.get("ok"):
                return res.get("url", "")
            raise RuntimeError(res.get("error", "알 수 없는 오류"))
    raise RuntimeError("Aside 응답이 없습니다: " + out[-400:])
