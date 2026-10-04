"""Build the one-page instructor profile PDF from profile/profile.yaml.

    .venv/bin/python scripts/make_profile.py

Output: profile/린쌤_강사소개.pdf (A4, one page). Needs Google Chrome for printing.
Lines containing [현장 확인] are highlighted so nothing unconfirmed goes out by accident.
"""
from __future__ import annotations

import base64
import html
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml  # noqa: E402

from autopost.upload_browser import chrome_path  # noqa: E402

FONT = ROOT / "assets" / "fonts" / "DoHyeon-Regular.ttf"
E = html.escape


def mark(text: str) -> str:
    t = E(text)
    return re.sub(r"\[현장 확인\]([^<]*)", r'<span class="todo">[현장 확인]\1</span>', t)


def thumb(vid: str, cache: Path) -> str:
    f = cache / f"{vid}.jpg"
    if not f.exists():
        try:
            req = urllib.request.Request(f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg", headers={"User-Agent": "Mozilla/5.0"})
            f.write_bytes(urllib.request.urlopen(req, timeout=15).read())
        except Exception:  # noqa: BLE001
            return ""
    return "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()


def build(data: dict, cache: Path) -> str:
    font = base64.b64encode(FONT.read_bytes()).decode()
    lis = lambda xs: "".join(f"<li>{mark(x)}</li>" for x in xs)  # noqa: E731
    rows = "".join(f"<tr><th>{mark(a)}</th><td>{mark(b)}</td></tr>" for a, b in data["programs"])
    vids = "".join(
        f'<a class="v" href="https://www.youtube.com/watch?v={v}"><img src="{thumb(v, cache)}" alt=""><b>{E(t)}</b><span>{mark(d)}</span></a>'
        for v, t, d in data["videos"])
    contact = "<br>".join(E(c) for c in data["contact"])
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{E(data['name'])}</title><style>
@font-face{{font-family:"DoHyeon";src:url(data:font/ttf;base64,{font}) format("truetype")}}
:root{{--ink:#231C29;--muted:#6D6475;--line:#E4DDE8;--accent:#B12D6C}}
*{{box-sizing:border-box}} body{{margin:0;color:var(--ink);font-family:"Apple SD Gothic Neo","Malgun Gothic",sans-serif;font-size:10.5pt;line-height:1.6}}
h1,h2{{font-family:"DoHyeon",sans-serif;font-weight:400;margin:0}} h1{{font-size:27pt;line-height:1.1}} h2{{font-size:14pt;color:var(--accent);margin-bottom:5px}}
.top{{display:grid;grid-template-columns:1fr auto;gap:16px;align-items:end;border-bottom:2.5pt solid var(--accent);padding-bottom:12px}}
.sub{{color:var(--muted);font-size:11pt;margin:4px 0 0}}
.contact{{text-align:right;font-size:9.5pt}} .contact b{{display:block;font-family:"DoHyeon";font-size:13pt;color:var(--accent);font-weight:400}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px 26px;margin-top:16px}}
ul{{margin:0;padding-left:1.1em}} li{{margin:2px 0}}
.todo{{background:#FFF0A8;padding:0 3px;border-radius:2px}}
table{{border-collapse:collapse;width:100%;font-size:10pt}} td,th{{border-bottom:.6pt solid var(--line);padding:4px 3px;text-align:left;vertical-align:top}} th{{font-weight:400;color:var(--muted);width:27%}}
.vids{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}}
.v{{text-decoration:none;color:var(--ink);display:grid;gap:2px;font-size:9pt}} .v img{{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:4px}} .v span{{color:var(--muted)}}
.full{{grid-column:1/-1}} .foot{{margin-top:14px;font-size:8.5pt;color:var(--muted);border-top:.6pt solid var(--line);padding-top:7px}}
@page{{size:A4;margin:14mm 14mm}}
</style></head><body>
<div class="top"><div><h1>{E(data['name'])}</h1><p class="sub">{E(data['subtitle'])}</p></div>
<div class="contact"><b>출강 문의</b>{contact}</div></div>
<div class="grid">
<section><h2>소속·자격</h2><ul>{lis(data['credentials'])}</ul></section>
<section><h2>출강 이력</h2><ul>{lis(data['centers'])}</ul></section>
<section class="full"><h2>가능한 수업</h2><table>{rows}</table></section>
<section class="full"><h2>수업 영상 (누르면 유튜브로 연결)</h2><div class="vids">{vids}</div></section>
</div><p class="foot">{E(data['footnote'])}</p></body></html>"""


def main() -> int:
    src = ROOT / "profile" / "profile.yaml"
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    cache = ROOT / "profile" / ".thumbs"
    cache.mkdir(parents=True, exist_ok=True)
    out = ROOT / "profile" / "린쌤_강사소개.pdf"
    with tempfile.TemporaryDirectory() as td:
        page = Path(td) / "profile.html"
        page.write_text(build(data, cache), encoding="utf-8")
        subprocess.run([chrome_path(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={out}", "--virtual-time-budget=4000", page.as_uri()],
                       check=True, capture_output=True)
    todo = sum(str(v).count("[현장 확인]") for v in data.values())
    print(f"PDF: {out}")
    if todo:
        print(f"※ [현장 확인] 항목 {todo}개가 남아 있습니다(노란 표시). 확인 후 profile.yaml 을 고치고 다시 만드세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
