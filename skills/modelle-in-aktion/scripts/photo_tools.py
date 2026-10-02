#!/usr/bin/env python3
"""Fotos sichten und vermessen – damit Koordinaten stimmen, bevor etwas animiert wird.

  photo_tools.py info  <foto>                         Größe (nach EXIF-Drehung), Seitenverhältnis
  photo_tools.py grid  <foto> <out.jpg> [--step 200] [--box x0 y0 x1 y1] [--width 1600]
        Verkleinerte Ansicht mit beschriftetem Koordinatengitter in ORIGINALPIXELN. Mit --box nur ein Ausschnitt
        (zum Hineinzoomen: erst grob, dann fein mit kleinerem --step). Daraus Polygone, Fußpunkte, Boxen ablesen.
  photo_tools.py crop  <foto> <out.jpg> x0 y0 x1 y1 [--sharpen]
        16:9-Ausschnitt (Box wird auf 16:9 korrigiert, Mitte bleibt) als 1920x1080, Lanczos, optional nachgeschärft.
  photo_tools.py boxes <foto> <out.jpg> <boxes.json> [--width 1600]
        Boxen/Polygone zur Kontrolle einzeichnen: {"name": [x0,y0,x1,y1] | [[x,y],…], …}
  photo_tools.py redact <bild> <out.jpg> x0 y0 x1 y1 [...]
        Rechtecke deckend übermalen (Namen auf Flipcharts, Gesichter) – vor jedem Upload, falls nötig.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stopmo.core import open_photo  # noqa: E402

FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Nunito-Bold.ttf"


def info(path):
    im = open_photo(path)
    w, h = im.size
    print(f"{path}: {w}x{h} ({w / h:.3f}, {'quer' if w > h else 'hoch'})")


def grid(path, out, step=200, box=None, width=1600):
    im = open_photo(path)
    x0, y0, x1, y1 = box or (0, 0, im.width, im.height)
    crop = im.crop((x0, y0, x1, y1))
    s = width / crop.width
    view = crop.resize((width, int(crop.height * s)), Image.LANCZOS).convert("RGB")
    d = ImageDraw.Draw(view, "RGBA")
    f = ImageFont.truetype(str(FONT), 15)
    gx = (x0 // step + 1) * step
    while gx < x1:
        X = (gx - x0) * s
        d.line([(X, 0), (X, view.height)], fill=(255, 0, 255, 150), width=1)
        d.rectangle([X + 2, 2, X + 46, 20], fill=(0, 0, 0, 170))
        d.text((X + 4, 2), str(gx), font=f, fill=(255, 255, 0))
        gx += step
    gy = (y0 // step + 1) * step
    while gy < y1:
        Y = (gy - y0) * s
        d.line([(0, Y), (view.width, Y)], fill=(0, 255, 255, 150), width=1)
        d.rectangle([2, Y + 2, 46, Y + 20], fill=(0, 0, 0, 170))
        d.text((4, Y + 2), str(gy), font=f, fill=(255, 255, 0))
        gy += step
    view.save(out, quality=88)
    print(f"{out}: Ausschnitt {x0},{y0}–{x1},{y1}, Gitter alle {step} px (Originalpixel)")


def crop16(path, out, box, sharpen=False):
    im = open_photo(path)
    x0, y0, x1, y1 = box
    cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    if w / h > 16 / 9:
        h = w * 9 / 16
    else:
        w = h * 16 / 9
    b = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    if b[0] < 0 or b[1] < 0 or b[2] > im.width or b[3] > im.height:
        print(f"Warnung: 16:9-Box {tuple(round(v) for v in b)} ragt aus dem Foto ({im.width}x{im.height})")
    res = im.resize((1920, 1080), Image.LANCZOS, box=b)
    if sharpen or w < 1920:
        res = res.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    res.save(out, quality=95)
    print(f"{out}: Box {tuple(round(v) for v in b)}, Faktor {1920 / w:.2f}" + (" (hochgerechnet!)" if w < 1920 else ""))


def boxes(path, out, spec, width=1600):
    im = open_photo(path)
    s = width / im.width
    view = im.resize((width, int(im.height * s)), Image.LANCZOS)
    d = ImageDraw.Draw(view)
    f = ImageFont.truetype(str(FONT), 18)
    items = json.loads(Path(spec).read_text())
    for name, v in items.items():
        if v and isinstance(v[0], (list, tuple)):
            d.polygon([(x * s, y * s) for x, y in v], outline=(255, 0, 255))
            tx, ty = v[0][0] * s, v[0][1] * s
        else:
            d.rectangle([v[0] * s, v[1] * s, v[2] * s, v[3] * s], outline=(255, 0, 255), width=2)
            tx, ty = v[0] * s, v[1] * s
        d.text((tx + 3, ty + 2), name, font=f, fill=(255, 255, 0), stroke_width=2, stroke_fill=(0, 0, 0))
    view.save(out, quality=88)
    print(out)


def redact(path, out, rects):
    im = open_photo(path)
    d = ImageDraw.Draw(im)
    for i in range(0, len(rects), 4):
        d.rectangle(rects[i:i + 4], fill=(128, 128, 128))
    im.save(out, quality=92)
    print(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info"); p.add_argument("photo")
    p = sub.add_parser("grid"); p.add_argument("photo"); p.add_argument("out")
    p.add_argument("--step", type=int, default=200); p.add_argument("--box", type=int, nargs=4)
    p.add_argument("--width", type=int, default=1600)
    p = sub.add_parser("crop"); p.add_argument("photo"); p.add_argument("out"); p.add_argument("box", type=float, nargs=4)
    p.add_argument("--sharpen", action="store_true")
    p = sub.add_parser("boxes"); p.add_argument("photo"); p.add_argument("out"); p.add_argument("spec")
    p.add_argument("--width", type=int, default=1600)
    p = sub.add_parser("redact"); p.add_argument("photo"); p.add_argument("out"); p.add_argument("rects", type=int, nargs="+")
    a = ap.parse_args()
    if a.cmd == "info":
        info(a.photo)
    elif a.cmd == "grid":
        grid(a.photo, a.out, a.step, a.box, a.width)
    elif a.cmd == "crop":
        crop16(a.photo, a.out, a.box, a.sharpen)
    elif a.cmd == "boxes":
        boxes(a.photo, a.out, a.spec, a.width)
    else:
        if len(a.rects) % 4:
            sys.exit("redact braucht Vierergruppen x0 y0 x1 y1")
        redact(a.photo, a.out, a.rects)


if __name__ == "__main__":
    main()
