"""Einblendungen: Bauchbinde je Modell, Titel, Schlussblock, Baustein-Piktogramm. Alles aus project.json (theme).

Gestaltung neutral und anpassbar: Schrift (Standard Nunito, liegt bei), Farben, optionale Kategorie-Marke über dem
Namen (z. B. »Wert 1«, »Team Nord«). Als Piktogramm dient ein schlichter Baustein mit zwei Noppen in der Modellfarbe –
im Titel als Reihe, die Stein für Stein aufleuchtet, im Schluss als Turm aus allen Steinen (»gemeinsam gebaut«).
Keine Markennamen in Texten: weder Hersteller der Steine noch Methode, außer der/die Nutzer:in will es ausdrücklich.

    from stopmo import overlays as O
    th = O.Theme.load("project.json")
    card = th.card(0)                 # PIL-RGBA, für build_final.py
    t = th.text_sprite("Unsere Werte …", "ink", 108)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
BUNDLED_FONTS = HERE.parent.parent / "assets" / "fonts"
GREY = (150, 142, 136)


def hex_rgb(v) -> tuple[int, int, int]:
    if isinstance(v, (list, tuple)):
        return tuple(int(x) for x in v[:3])
    v = v.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def balanced_lines(text: str, font: ImageFont.FreeTypeFont, max_w: float) -> list[str]:
    """Eine Zeile, wenn sie passt; sonst zwei möglichst gleich lange (kein einzelnes Wort in Zeile 2)."""
    if font.getlength(text) <= max_w:
        return [text]
    words = text.split()
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        w = max(font.getlength(a), font.getlength(b))
        if best is None or w < best[0]:
            best = (w, [a, b])
    return best[1] if best else [text]


def shadowed(img: Image.Image, blur=16, alpha=70, dy=6, pad=20) -> Image.Image:
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 255), (pad, pad + dy), img.split()[3].point(lambda a: alpha if a > 0 else 0))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    out.alpha_composite(img, (pad, pad))
    return out


def brick(size: int, color, studs=2, pop=1.0, outline=None) -> Image.Image:
    """Baustein in leichter Aufsicht (Vorderseite + Oberseite + Noppen), quadratisches RGBA-Bild.
    pop > 1 lässt ihn kurz anwachsen (Stop-Motion-Hüpfer)."""
    S = size * 4
    im = Image.new("RGBA", (S, S), tuple(color[:3]) + (0,))
    d = ImageDraw.Draw(im)
    g = pop
    col = tuple(color[:3])
    light = tuple(min(255, int(v + (255 - v) * 0.28)) for v in col) + (255,)
    dark = tuple(int(v * 0.72) for v in col) + (255,)
    base = tuple(col) + (255,)
    bw = 0.84 * S * g                    # Breite
    fh = 0.36 * S * g                    # Höhe der Vorderseite
    th = 0.16 * S * g                    # Tiefe der Oberseite (Aufsicht)
    cx, bottom = S / 2, S * 0.90
    x0, x1 = cx - bw / 2, cx + bw / 2
    fy0 = bottom - fh
    r = S * 0.035
    # Oberseite (hell) und Vorderseite (Grundfarbe), Unterkante dunkel
    d.rounded_rectangle([x0, fy0 - th, x1, fy0 + r], radius=r, fill=light)
    d.rounded_rectangle([x0, fy0, x1, bottom], radius=r, fill=base)
    d.rectangle([x0 + r, bottom - fh * 0.12, x1 - r, bottom - 1], fill=dark)
    d.rounded_rectangle([x0, bottom - fh * 0.14, x1, bottom], radius=r, fill=dark)
    d.rectangle([x0 + r, fy0 - 1, x1 - r, fy0 + S * 0.012], fill=dark)  # Kante Oberseite/Vorderseite
    # Noppen: Zylinder auf der Oberseite (Seite in Grundfarbe, Deckel hell)
    sw = bw / (studs * 1.75)
    gap = (bw - studs * sw) / studs
    sh = 0.13 * S * g
    ey = th * 0.55
    for k in range(studs):
        sx = x0 + gap / 2 + k * (sw + gap)
        top = fy0 - th / 2 - sh
        d.rectangle([sx, top + ey / 2, sx + sw, fy0 - th / 2 + ey / 2 - 2], fill=base)
        d.ellipse([sx, fy0 - th / 2 - ey / 2 + ey / 2 - 2, sx + sw, fy0 - th / 2 + ey - 2], fill=dark)
        d.rectangle([sx, top + ey / 2, sx + sw, fy0 - th / 2 + ey / 2 - 2], fill=base)
        d.ellipse([sx, top, sx + sw, top + ey], fill=light)
    if outline:
        d.rounded_rectangle([x0, fy0 - th, x1, bottom], radius=r, outline=tuple(outline) + (255,), width=int(S * 0.02))
    return im.resize((size, size), Image.LANCZOS)


def tower(width: int, colors: list, lit: int, pop_idx=-1, pop=1.0, base=GREY) -> Image.Image:
    """Turm aus len(colors) Steinen (unten der erste). lit = wie viele schon in Farbe sind."""
    n = len(colors)
    step = int(width * 0.40)
    h = step * (n - 1) + width
    im = Image.new("RGBA", (int(width * 1.3), h), (0, 0, 0, 0))
    for k in range(n):
        col = colors[k] if k < lit else base
        b = brick(width, col, pop=pop if k == pop_idx else 1.0)
        off = int(width * 0.06) * (1 if k % 2 else -1)  # leicht versetzt gestapelt
        im.alpha_composite(b, (int(width * 0.15) + off, h - width - k * step))
    return im


class Theme:
    def __init__(self, cfg: dict, root: Path):
        self.cfg = cfg
        self.root = root
        th = cfg.get("theme", {})
        self.ink = hex_rgb(th.get("ink", "#231F20"))
        self.accent = hex_rgb(th.get("accent", "#E7362C"))
        self.muted = hex_rgb(th.get("muted", "#504A46"))
        self.card_bg = hex_rgb(th.get("card_bg", "#FFFFFF"))
        self.family = th.get("font_family", "Nunito")
        fd = th.get("font_dir")
        self.font_dir = (root / fd) if fd else BUNDLED_FONTS
        self.models = cfg["models"]
        self.colors = [hex_rgb(m["color"]) for m in self.models]

    @classmethod
    def load(cls, path="project.json") -> "Theme":
        p = Path(path).resolve()
        return cls(json.loads(p.read_text()), p.parent)

    def color(self, name):
        return {"ink": self.ink, "accent": self.accent, "muted": self.muted}.get(name) or hex_rgb(name)

    def font(self, weight: str, size: int) -> ImageFont.FreeTypeFont:
        for cand in (self.font_dir / f"{self.family}-{weight}.ttf", BUNDLED_FONTS / f"Nunito-{weight}.ttf"):
            if cand.exists():
                return ImageFont.truetype(str(cand), size)
        return ImageFont.truetype(str(BUNDLED_FONTS / "Nunito-Bold.ttf"), size)

    # ---------- Bauchbinde ----------
    def card(self, idx: int, pop: float = 1.0, max_w: int = 960) -> Image.Image:
        """Weiße Karte oben links: Farbstreifen, Baustein, optionale Marke, Name, Claim (max. 2 Zeilen)."""
        m = self.models[idx]
        color = self.colors[idx]
        label, value, claim = m.get("label", ""), m["name"], m.get("claim", "")
        icon, pad = 108, 26
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        f_claim = self.font("SemiBold", 31)
        lines = m.get("claim_lines") or (balanced_lines(claim, f_claim, 560) if claim else [])
        vsize = 58
        while True:
            f_value = self.font("Black", vsize)
            text_w = max([probe.textlength(value, font=f_value)] + [probe.textlength(c, font=f_claim) for c in lines])
            cw = int(pad + icon + 26 + text_w + pad + 6)
            if cw <= max_w or vsize <= 40:
                break
            vsize -= 2
        f_label = self.font("ExtraBold", 25)
        top = 60 if label else 24
        ch = top + 72 + 38 * len(lines) + (18 if lines else 0)
        ch = max(ch, icon + 2 * 22)
        c = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cd = ImageDraw.Draw(c)
        cd.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=26, fill=self.card_bg + (242,))
        alpha = c.split()[3]
        stripe = Image.new("L", c.size, 0)
        ImageDraw.Draw(stripe).rectangle([0, 0, 11, ch], fill=255)
        c.paste(color + (255,), (0, 0), Image.fromarray(np.minimum(np.asarray(alpha), np.asarray(stripe))))
        c.alpha_composite(brick(icon, color, pop=pop), (pad, (ch - icon) // 2))
        tx = pad + icon + 26
        if label:
            lw = probe.textlength(label.upper(), font=f_label)
            cd.rounded_rectangle([tx, 22, tx + lw + 30, 55], radius=17, fill=color + (255,))
            cd.text((tx + 15, 24), label.upper(), font=f_label, fill="white")
        cd.text((tx - 2, top + (58 - vsize) // 2), value, font=f_value, fill=self.ink + (255,))
        for i, line in enumerate(lines):
            cd.text((tx, top + 72 + 38 * i), line, font=f_claim, fill=self.muted + (255,))
        return shadowed(c)

    # ---------- Texte ----------
    def text_sprite(self, text: str, color, px: int, weight="Black", shadow=(4, 3, 0.25)) -> Image.Image:
        """Text als RGBA mit weichem Schatten (liegt »auf dem Tisch«)."""
        f = self.font(weight, max(8, int(px)))
        col = self.color(color) if isinstance(color, str) else tuple(color)
        x0, y0, x1, y1 = f.getbbox(text)
        pad = 24
        im = Image.new("RGBA", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pad - x0, pad - y0), text, font=f, fill=col + (255,))
        if shadow:
            dy, blur, op = shadow
            sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
            sh.paste((30, 20, 10, 255), (0, dy), im.split()[3].point(lambda a: int(a * op)))
            out = sh.filter(ImageFilter.GaussianBlur(blur))
            out.alpha_composite(im)
            return out
        return im

    def runs_sprite(self, runs: list, px: int, weight="Black") -> Image.Image:
        """Mehrfarbige Zeile: runs = [[text, farbe], …]."""
        parts = [self.text_sprite(t, c, px, weight) for t, c in runs]
        f = self.font(weight, px)
        widths = [f.getlength(t) for t, _ in runs]
        H = max(p.height for p in parts)
        im = Image.new("RGBA", (int(sum(widths)) + 48, H), (0, 0, 0, 0))
        x = 0.0
        for p, w in zip(parts, widths):
            im.alpha_composite(p, (int(x), 0))
            x += w
        return im

    def brick_row(self, lit: int, size=84, gap=22, pop_idx=-1, pop=1.0) -> Image.Image:
        """Reihe grauer Steine; die ersten lit leuchten in ihren Farben (Titel)."""
        n = len(self.colors)
        im = Image.new("RGBA", (n * size + (n - 1) * gap, size), (0, 0, 0, 0))
        for k, col in enumerate(self.colors):
            b = brick(size, col if k < lit else GREY, pop=pop if k == pop_idx else 1.0)
            im.alpha_composite(b, (k * (size + gap), 0))
        return shadowed(im, blur=8, alpha=60, dy=5)

    def tower(self, width=150, lit=None, pop_idx=-1, pop=1.0) -> Image.Image:
        lit = len(self.colors) if lit is None else lit
        return shadowed(tower(width, self.colors, lit, pop_idx, pop), blur=9, alpha=70, dy=7)


def pop_curve(i: int, at: int, rest=1.0, seq=(1.15, 0.97, 1.0)) -> float:
    """Pop eines Elements, das in Bild at erscheint: 115 % -> 97 % -> 100 % (Stop-Motion-Hüpfer)."""
    k = i - at
    if k < 0:
        return 0.0
    return seq[k] * rest if k < len(seq) else rest


def place(canvas: Image.Image, sprite: Image.Image, center, scale=1.0) -> None:
    """Sprite (RGBA) zentriert auf center setzen, optional skaliert."""
    if scale <= 0:
        return
    sp = sprite if abs(scale - 1) < 1e-3 else sprite.resize(
        (max(1, int(sprite.width * scale)), max(1, int(sprite.height * scale))), Image.LANCZOS)
    canvas.alpha_composite(sp, (int(center[0] - sp.width / 2), int(center[1] - sp.height / 2)))


def place_left(canvas: Image.Image, sprite: Image.Image, x, cy, scale=1.0) -> None:
    """Linksbündig (Textblöcke poppen nach rechts, linke Kante bleibt)."""
    if scale <= 0:
        return
    sp = sprite if abs(scale - 1) < 1e-3 else sprite.resize(
        (max(1, int(sprite.width * scale)), max(1, int(sprite.height * scale))), Image.LANCZOS)
    canvas.alpha_composite(sp, (int(x), int(cy - sp.height / 2)))


def composite(frame: np.ndarray, layer: Image.Image) -> np.ndarray:
    """RGBA-Ebene (Bildgröße) über ein float32-Bild legen."""
    a = np.asarray(layer).astype(np.float32)
    al = a[..., 3:4] / 255.0
    return frame * (1 - al) + a[..., :3] * al


def ease_back(u: float) -> float:
    """Überschwingen (für Grafik, die »einrastet«)."""
    u = max(0.0, min(1.0, u))
    s = 1.70158
    return 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2


__all__ = ["Theme", "brick", "tower", "pop_curve", "place", "place_left", "composite", "hex_rgb", "balanced_lines",
           "math"]
