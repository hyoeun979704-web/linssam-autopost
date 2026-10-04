"""Turn a raw phone clip into a finished 1080x1920 short or a 1920x1080 long video.

Steps: probe -> trim -> find the dancer -> crop -> overlays (title band, beat counts,
end card) -> render with ffmpeg -> thumbnail -> quality check.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import FONT

SHORT_W, SHORT_H = 1080, 1920
LONG_W, LONG_H = 1920, 1080


@dataclass
class Probe:
    width: int
    height: int
    duration: float
    fps: float
    has_audio: bool


@dataclass
class EditResult:
    video: Path
    thumbnail: Path
    duration: float
    problems: list[str] = field(default_factory=list)   # stop: goes to 확인필요
    warnings: list[str] = field(default_factory=list)   # note in the log, still uploads


def run(cmd: list[str], cwd: str | Path | None = None) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd) if cwd else None)
    if p.returncode != 0:
        raise RuntimeError(f"{cmd[0]} 실패: {p.stderr[-800:]}")
    return p.stdout


def probe(path: Path) -> Probe:
    out = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    info = json.loads(out)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = int(v.get("tags", {}).get("rotate", rot))
    if abs(rot) in (90, 270):
        w, h = h, w
    num, den = (v.get("avg_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den) if float(den) else 30.0
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    return Probe(w, h, float(info["format"]["duration"]), fps, has_audio)


# ---------- dancer position ----------

def dancer_boxes(path: Path, start: float, end: float, samples: int = 12) -> list[tuple[int, int, int, int]]:
    """Return person boxes (x, y, w, h) found in evenly spaced frames, in display orientation."""
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    cap = cv2.VideoCapture(str(path))
    boxes = []
    for t in np.linspace(start, end, samples + 2)[1:-1]:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        scale = 640 / max(frame.shape[:2])
        small = cv2.resize(frame, None, fx=scale, fy=scale)
        rects, weights = hog.detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)
        if len(rects):
            i = int(np.argmax(weights))
            x, y, w, h = (np.array(rects[i]) / scale).astype(int)
            boxes.append((int(x), int(y), int(w), int(h)))
    cap.release()
    return boxes


def dancer_track(path: Path, start: float, end: float, step: float = 0.33) -> list[tuple[float, float | None, float | None]]:
    """(time from start, center x, box bottom) every `step` seconds; None where nobody was found."""
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    cap = cv2.VideoCapture(str(path))
    out = []
    t = start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        cx = bottom = None
        if ok:
            scale = 512 / max(frame.shape[:2])
            small = cv2.resize(frame, None, fx=scale, fy=scale)
            rects, weights = hog.detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)
            if len(rects):
                i = int(np.argmax(weights))
                x, y, w, h = np.array(rects[i]) / scale
                cx, bottom = float(x + w / 2), float(y + h)
        out.append((t - start, cx, bottom))
        t += step
    cap.release()
    return out


def smooth_path(track, default: float) -> list[tuple[float, float]]:
    ts = np.array([t for t, _, _ in track])
    xs = np.array([np.nan if c is None else c for _, c, _ in track], dtype=float)
    if np.all(np.isnan(xs)):
        return [(float(t), default) for t in ts]
    good = ~np.isnan(xs)
    xs = np.interp(ts, ts[good], xs[good])
    # median over 5 samples kills one-off false detections, then an easing pass
    med = np.array([np.median(xs[max(0, i - 2):i + 3]) for i in range(len(xs))])
    out = []
    cur = med[0]
    for t, v in zip(ts, med):
        cur = cur + 0.35 * (v - cur)
        out.append((float(t), float(cur)))
    return out


# ---------- beats ----------

def beat_times(path: Path, start: float, end: float) -> list[float]:
    try:
        import librosa
    except ImportError:
        return []
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(path),
             "-vn", "-ac", "1", "-ar", "22050", str(wav)])
        y, sr = librosa.load(str(wav), sr=22050)
    if len(y) < sr:
        return []
    _, frames = librosa.beat.beat_track(y=y, sr=sr)
    return [float(t) for t in librosa.frames_to_time(frames, sr=sr)]


# ---------- overlay images ----------

def clean(text: str) -> str:
    """Do Hyeon has no middle dot; use a spaced hyphen instead."""
    return text.replace("·", "-").replace("•", "-")


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size)


def title_band(text: str, width: int, path: Path) -> int:
    """Draw the fixed top band. Returns its height."""
    text = clean(text)
    size = int(width * 0.075)
    font = _font(size)
    while font.getlength(text) > width * 0.9 and size > 30:
        size -= 4
        font = _font(size)
    pad = int(size * 0.55)
    h = size + pad * 2
    img = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, h], fill=(24, 18, 30, 200))
    tw = font.getlength(text)
    d.text(((width - tw) / 2, pad - size * 0.08), text, font=font, fill=(255, 255, 255, 255))
    img.save(path)
    return h


def count_badge(n: int, width: int, path: Path) -> None:
    size = int(width * 0.11)
    font = _font(size)
    box = int(size * 1.5)
    img = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, box - 1, box - 1], fill=(177, 45, 108, 230))
    t = str(n)
    tw = font.getlength(t)
    d.text(((box - tw) / 2, (box - size) / 2 - size * 0.08), t, font=font, fill=(255, 255, 255, 255))
    img.save(path)


def end_card(text: str, width: int, height: int, path: Path) -> None:
    text = clean(text)
    size = int(width * 0.06)
    font = _font(size)
    while font.getlength(text) > width * 0.86 and size > 28:
        size -= 3
        font = _font(size)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bh = int(size * 2.2)
    top = int(height * 0.10) + int(width * 0.075) * 2  # below the title band
    d.rounded_rectangle([int(width * 0.05), top, int(width * 0.95), top + bh], radius=int(bh * 0.3), fill=(255, 255, 255, 235))
    tw = font.getlength(text)
    d.text(((width - tw) / 2, top + (bh - size) / 2 - size * 0.08), text, font=font, fill=(35, 28, 41, 255))
    img.save(path)


# ---------- render ----------

def _between(times: list[tuple[float, float]]) -> str:
    return "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in times) or "0"


def render(src: Path, out_dir: Path, *, kind: str, title: str, class_line: str, opts: dict,
           out_stem: str | None = None) -> EditResult:
    """kind: 'shorts' or 'long'."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pr = probe(src)
    problems: list[str] = []
    warnings: list[str] = []
    start = min(opts.get("trim_head_sec", 0.5), pr.duration * 0.1)
    end = max(start + 1.0, pr.duration - opts.get("trim_tail_sec", 0.5))
    dur = end - start

    W, H = (SHORT_W, SHORT_H) if kind == "shorts" else (LONG_W, LONG_H)
    target_ratio = W / H
    track = dancer_track(src, start, end)
    found = [c for _, c, _ in track if c is not None]
    if len(found) < max(3, len(track) * 0.3):
        problems.append("사람을 잘 찾지 못했습니다. 화면 가운데 기준으로 잘랐으니 결과를 확인해 주세요.")
    bottoms = [b for _, _, b in track if b is not None]
    if bottoms and np.median(bottoms) > pr.height * 0.985:
        problems.append("발끝이 화면 아래에 걸려 잘렸을 수 있습니다.")

    src_ratio = pr.width / pr.height
    sendcmd = None
    if src_ratio > target_ratio + 0.01:  # wider source: a window that follows the dancer
        cw = int(pr.height * target_ratio) // 2 * 2
        path_ = smooth_path(track, pr.width / 2)
        lines = []
        for t, cx in path_:
            x0 = int(min(max(cx - cw / 2, 0), pr.width - cw))
            lines.append(f"{t:.3f} crop x {x0};")
        x_first = lines[0].split()[-1].rstrip(";") if lines else 0
        crop = f"crop={cw}:{pr.height}:{x_first}:0"
        sendcmd = "\n".join(lines)
    elif src_ratio < target_ratio - 0.01:  # taller source: keep the bottom so the feet stay in
        ch = int(pr.width / target_ratio) // 2 * 2
        cy0 = max(pr.height - ch, 0) // 2
        crop = f"crop={pr.width}:{ch}:0:{cy0}"
    else:
        crop = "null"
    if kind == "shorts" and src_ratio > 1.0:
        warnings.append("가로로 찍은 영상이라 세로로 잘랐습니다. 세로로 찍으면 화면이 더 크게 나옵니다.")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        inputs = ["-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(src.resolve())]
        pre = ""
        if sendcmd:
            cmdfile = td / "crop.cmd"
            cmdfile.write_text(sendcmd.replace("\\n", "\n"), encoding="utf-8")
            pre = "sendcmd=f=crop.cmd,"  # relative path: ffmpeg runs inside td (Windows drive colons break filters)
        filters = [f"[0:v]setpts=PTS-STARTPTS,{pre}{crop},scale={W}:{H}:flags=lanczos,setsar=1,fps=30[base]"]
        last = "base"
        idx = 1
        if kind == "shorts":
            band = td / "band.png"
            title_band(title, W, band)
            inputs += ["-loop", "1", "-i", str(band)]
            filters.append(f"[{last}][{idx}:v]overlay=0:{int(H * 0.06)}:shortest=1[v{idx}]")
            last, idx = f"v{idx}", idx + 1

        if opts.get("count_captions", True) and pr.has_audio:
            beats = beat_times(src, start, end)
            if len(beats) >= 8:
                spans: dict[int, list[tuple[float, float]]] = {n: [] for n in range(1, 9)}
                card_from = dur - opts.get("end_card_sec", 2.0) if class_line else dur
                for i, b in enumerate(beats):
                    if b >= card_from - 0.2:
                        break
                    nxt = beats[i + 1] if i + 1 < len(beats) else b + 0.4
                    spans[(i % 8) + 1].append((b, min(nxt, b + 0.45)))
                y_count = int(H * 0.06) + int(W * 0.075) * 2 + 24 if kind == "shorts" else int(H * 0.06)
                for n in range(1, 9):
                    badge = td / f"c{n}.png"
                    count_badge(n, W if kind == "shorts" else int(W * 0.6), badge)
                    inputs += ["-loop", "1", "-i", str(badge)]
                    filters.append(
                        f"[{last}][{idx}:v]overlay=W-w-{int(W * 0.05)}:{y_count}:shortest=1:enable='{_between(spans[n])}'[v{idx}]")
                    last, idx = f"v{idx}", idx + 1
            else:
                warnings.append("박자를 찾지 못해 카운트 자막을 넣지 않았습니다.")

        ec_sec = opts.get("end_card_sec", 2.0)
        if class_line and dur > ec_sec + 1:
            card = td / "end.png"
            end_card(class_line, W, H, card)
            inputs += ["-loop", "1", "-i", str(card)]
            filters.append(f"[{last}][{idx}:v]overlay=0:0:shortest=1:enable='gte(t,{dur - ec_sec:.3f})'[v{idx}]")
            last, idx = f"v{idx}", idx + 1

        out = (out_dir / f"{out_stem or src.stem}_{kind}.mp4").resolve()
        cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", f"[{last}]"]
        if pr.has_audio:
            cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(out)]
        run(cmd, cwd=td)

    thumb = out_dir / f"{out_stem or src.stem}_{kind}_thumb.jpg"
    make_thumbnail(src, best_front_frame(src, start, end), thumb, title, kind, crop if kind == "shorts" else None)
    final = probe(out)
    if kind == "shorts" and final.duration > opts.get("max_shorts_sec", 60):
        problems.append(f"쇼츠인데 {final.duration:.0f}초입니다(최대 {opts.get('max_shorts_sec', 60)}초).")
    return EditResult(out, thumb, final.duration, problems, warnings)


def best_front_frame(src: Path, start: float, end: float, n: int = 24) -> float:
    """Time of the frame with the largest frontal face (the teacher facing camera)."""
    face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(src))
    best_t, best_area = start + (end - start) * 0.4, 0
    for t in np.linspace(start + (end - start) * 0.1, end - (end - start) * 0.1, n):
        cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face.detectMultiScale(g, 1.1, 6, minSize=(24, 24))
        for (x, y, w, h) in faces:
            if w * h > best_area:
                best_t, best_area = float(t), w * h
    cap.release()
    return best_t


def make_thumbnail(src: Path, at: float, thumb: Path, title: str, kind: str, crop: str | None = None) -> None:
    """Frame from the source (no count badges). Long videos get the title on the empty side
    of the frame, away from the dancer, so face and feet stay visible."""
    title = clean(title)
    with tempfile.TemporaryDirectory() as td:
        frame = Path(td) / "f.jpg"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1", "-q:v", "2", str(frame)])
        img = Image.open(frame).convert("RGB")
    if kind != "long":
        img.save(thumb, quality=90)
        return
    img = img.resize((1280, 720))
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    rects, w8 = hog.detectMultiScale(arr, winStride=(8, 8), padding=(8, 8), scale=1.05)
    if len(rects):
        bx, _, bw, _ = rects[int(np.argmax(w8))]
    else:
        bx, bw = 540, 200
    cx = bx + bw / 2
    left = cx > 640  # dancer on the right -> text on the left
    parts = [p.strip() for p in title.split(" - ", 1)]
    d = ImageDraw.Draw(img, "RGBA")
    x0, x1 = (50, max(420, bx - 40)) if left else (min(860, bx + bw + 40), 1230)
    y = 220
    for i, line in enumerate(parts):
        size = 110 if i == 0 else 64
        font = _font(size)
        while font.getlength(line) > (x1 - x0) and size > 36:
            size -= 4
            font = _font(size)
        tw = font.getlength(line)
        pad = 18
        d.rounded_rectangle([x0 - pad, y - pad // 2, x0 + tw + pad, y + size + pad], radius=16,
                            fill=(24, 18, 30, 215) if i == 0 else (177, 45, 108, 235))
        d.text((x0, y), line, font=font, fill=(255, 255, 255, 255))
        y += size + 44
    img.save(thumb, quality=90)


def has_tool(name: str) -> bool:
    return shutil.which(name) is not None
