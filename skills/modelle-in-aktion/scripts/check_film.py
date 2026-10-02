#!/usr/bin/env python3
"""Endkontrolle eines Films oder Segments: Dauer, Bildrate, Lautheit, Kontaktbögen.

    python3 check_film.py output/film.mp4 [--every 0.5] [--out sheets/film]

Schreibt Kontaktbögen (12 Bilder je Bogen, Zeitstempel im Bild) und gibt Lautheit/Spitze aus.
Die Bögen IMMER ansehen: Text am Rand angeschnitten? Figur verdoppelt/verbogen? Bauchbinde über der Aktion?
Markennamen oder Klarnamen im Bild (auch auf Kärtchen, Flipcharts, Verpackungen im Hintergrund)?
"""
import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,"
                        "r_frame_rate", "-of", "json", path], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    t = r.stderr
    if "{" not in t:
        return None
    return json.loads(t[t.rfind("{"):t.rfind("}") + 1])


def sheets(path, out, every, dur):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    times = [round(i * every, 3) for i in range(int(dur / every) + 1)]
    thumbs = []
    for t in times:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-vf",
                              "scale=480:-1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        if raw:
            from io import BytesIO
            thumbs.append((t, Image.open(BytesIO(raw)).convert("RGB")))
    files = []
    for s in range(0, len(thumbs), 12):
        part = thumbs[s:s + 12]
        w, h = part[0][1].size
        im = Image.new("RGB", (4 * w, 3 * h), (20, 20, 20))
        d = ImageDraw.Draw(im)
        for k, (t, th) in enumerate(part):
            x, y = (k % 4) * w, (k // 4) * h
            im.paste(th, (x, y))
            d.rectangle([x + 2, y + 2, x + 64, y + 18], fill=(0, 0, 0))
            d.text((x + 6, y + 4), f"{t:.2f} s", fill=(255, 255, 0))
        f = f"{out}-{s // 12 + 1}.jpg"
        im.save(f, quality=85)
        files.append(f)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--every", type=float, default=0.5)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    p = probe(a.video)
    dur = float(p["format"]["duration"])
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in p["streams"])
    print(f"{a.video}: {dur:.2f} s, {v['width']}x{v['height']}, {v['r_frame_rate']} fps, Ton: {'ja' if has_audio else 'nein'}")
    if has_audio:
        m = loudness(a.video)
        if m:
            print(f"Lautheit {m['input_i']} LUFS, Spitze {m['input_tp']} dBTP")
    out = a.out or f"sheets/{Path(a.video).stem}"
    for f in sheets(a.video, out, a.every, dur):
        print(f)


if __name__ == "__main__":
    main()
