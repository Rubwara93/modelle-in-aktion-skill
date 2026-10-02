"""Virtuelle Kamera über dem Originalfoto.

Statt ein 1920x1080-Bild digital aufzublasen, wird jedes Bild direkt aus dem hochaufgelösten Foto ausgeschnitten
(»World«). So bleibt eine Nahaufnahme scharf, und Totale, Push-in und Zoom raus teilen sich dieselbe Geometrie.
Ausschnitte (boxes) sind (x0, y0, x1, y1) in Fotopixeln, immer 16:9.

Bewegungsgrammatik (siehe references/rhythmus.md):
  * Kamera fährt »auf Einsen«: jedes 12-fps-Bild ein Schritt, sonst ruckelt die Fahrt doppelt.
  * Push-in und Zoom raus geometrisch interpolieren (lerp_box), damit der Zoom gleichmäßig wirkt.
  * Rein- und Rauszoomen um denselben Fixpunkt (fixpoint), dann landet der Zoom raus exakt in der Totale.

    from stopmo import camera as K
    world = K.World("input/model-a.jpg")
    tot = world.fit_box()                         # größte 16:9-Box im Foto
    nah = K.box_around((2400, 1800), 1500)        # 1500 px breit um die Hauptfigur
    for i in range(12):
        box = K.lerp_box(tot, nah, C.ease(i / 11), world.size)
        frame = world.shoot(box)
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .core import H, W, open_photo, to_img

ASPECT = W / H


class World:
    """Hochaufgelöstes Foto (oder ein bereinigtes Weltbild) als Quelle aller Kameraausschnitte."""

    def __init__(self, src, pad_top: int = 0):
        if isinstance(src, str):
            im = open_photo(src)
        elif isinstance(src, np.ndarray):
            im = to_img(src)
        else:
            im = src.convert("RGB")
        if pad_top:
            # oben Platz schaffen (Kopffreiheit), Rand wird aus der obersten Zeile fortgesetzt
            ext = Image.new("RGB", (im.width, im.height + pad_top))
            ext.paste(im.crop((0, 0, im.width, 1)).resize((im.width, pad_top)), (0, 0))
            ext.paste(im, (0, pad_top))
            im = ext
        self.im = im
        self.size = im.size
        self._cache: dict = {}

    def array(self) -> np.ndarray:
        return np.asarray(self.im).astype(np.float32)

    def shoot(self, box, cache=True) -> np.ndarray:
        """Ausschnitt box (Fotopixel) als 1920x1080-Bild."""
        key = tuple(round(float(v), 2) for v in box)
        if cache and key in self._cache:
            return self._cache[key].copy()
        a = np.asarray(self.im.resize((W, H), Image.LANCZOS, box=key)).astype(np.float32)
        if cache:
            if len(self._cache) > 64:
                self._cache.clear()
            self._cache[key] = a
        return a.copy()

    def fit_box(self, anchor="center") -> tuple:
        """Größte 16:9-Box, die ins Foto passt (anchor: center | top | bottom)."""
        w, h = self.size
        if w / h > ASPECT:
            bw, bh = h * ASPECT, h
        else:
            bw, bh = w, w / ASPECT
        x0 = (w - bw) / 2
        y0 = {"top": 0.0, "bottom": h - bh}.get(anchor, (h - bh) / 2)
        return (x0, y0, x0 + bw, y0 + bh)


def shoot_array(arr: np.ndarray, box, origin=(0, 0)) -> np.ndarray:
    """Wie World.shoot, aber direkt aus einem (Teil-)Weltbild als Array, dessen Ecke bei origin liegt.
    Schneidet erst knapp aus und wandelt nur diesen Teil – viel schneller als ein ganzes 24-MP-Bild."""
    x0, y0, x1, y1 = [float(v) for v in box]
    ox, oy = origin
    cx0, cy0 = max(0, int(x0 - ox) - 2), max(0, int(y0 - oy) - 2)
    cx1, cy1 = min(arr.shape[1], int(x1 - ox) + 3), min(arr.shape[0], int(y1 - oy) + 3)
    sub = to_img(arr[cy0:cy1, cx0:cx1])
    b = (x0 - ox - cx0, y0 - oy - cy0, x1 - ox - cx0, y1 - oy - cy0)
    return np.asarray(sub.resize((W, H), Image.LANCZOS, box=b)).astype(np.float32)


def union_box(*boxes) -> tuple[int, int, int, int]:
    return (int(min(b[0] for b in boxes)), int(min(b[1] for b in boxes)),
            int(np.ceil(max(b[2] for b in boxes))), int(np.ceil(max(b[3] for b in boxes))))


def box_around(center, width) -> tuple:
    cx, cy = center
    h = width / ASPECT
    return (cx - width / 2, cy - h / 2, cx + width / 2, cy + h / 2)


def clamp_box(box, size) -> tuple:
    """Box ins Foto schieben (Größe bleibt, sofern sie passt)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    sw, sh = size
    x0 = min(max(x0, 0), max(0, sw - w))
    y0 = min(max(y0, 0), max(0, sh - h))
    return (x0, y0, x0 + w, y0 + h)


def zoom_box(box, z, focus) -> tuple:
    """Ausschnitt um den Faktor z verkleinern; focus (Fotopixel) bleibt an seiner Bildstelle."""
    x0, y0, x1, y1 = box
    fx, fy = focus
    return (fx - (fx - x0) / z, fy - (fy - y0) / z, fx + (x1 - fx) / z, fy + (y1 - fy) / z)


def lerp_box(a, b, u, size=None) -> tuple:
    """Zwischen zwei 16:9-Ausschnitten: Mitte linear, Breite geometrisch (gleichmäßig wirkender Zoom)."""
    cxa, cya, wa = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2, a[2] - a[0]
    cxb, cyb, wb = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, b[2] - b[0]
    cx, cy = cxa + (cxb - cxa) * u, cya + (cyb - cya) * u
    w = wa * (wb / wa) ** u
    box = (cx - w / 2, cy - w / ASPECT / 2, cx + w / 2, cy + w / ASPECT / 2)
    return clamp_box(box, size) if size else box


def fixpoint(A, B):
    """Fixpunkt p und Faktor k der Zentralstreckung mit B = p + k (A - p). Wer um p zoomt, landet exakt in B."""
    k = (B[2] - B[0]) / (A[2] - A[0])
    if abs(1 - k) < 1e-9:
        return ((A[0] + A[2]) / 2, (A[1] + A[3]) / 2), 1.0
    return ((B[0] - k * A[0]) / (1 - k), (B[1] - k * A[1]) / (1 - k)), k


def window(A, p, s) -> tuple:
    """Box A um Fixpunkt p mit Faktor s gestreckt (s = 1: A, s = k: B)."""
    return (p[0] + s * (A[0] - p[0]), p[1] + s * (A[1] - p[1]), p[0] + s * (A[2] - p[0]), p[1] + s * (A[3] - p[1]))


def zoom_path(A, B, n: int, curve=None) -> list[tuple]:
    """n Ausschnitte von A nach B um den gemeinsamen Fixpunkt (Faktor geometrisch, curve = Easing auf 0..1)."""
    p, k = fixpoint(A, B)
    out = []
    for j in range(n):
        u = j / max(1, n - 1)
        if curve:
            u = curve(u)
        out.append(window(A, p, k ** u))
    return out


def to_screen(pt, box) -> tuple[float, float]:
    """Fotopunkt -> Bildpunkt (1920x1080) im Ausschnitt box."""
    return ((pt[0] - box[0]) / (box[2] - box[0]) * W, (pt[1] - box[1]) / (box[3] - box[1]) * H)


def to_photo(pt, box) -> tuple[float, float]:
    """Bildpunkt -> Fotopunkt."""
    return (box[0] + pt[0] / W * (box[2] - box[0]), box[1] + pt[1] / H * (box[3] - box[1]))


def scale_of(box) -> float:
    """Fotopixel je Bildpixel (für Hub-Höhen, Schattengrößen usw.)."""
    return (box[2] - box[0]) / W
