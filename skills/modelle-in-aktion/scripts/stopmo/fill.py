"""Flächen füllen, die eine bewegte Figur freilegt.

Wenn eine Figur hüpft oder sich dreht, wird darunter etwas sichtbar, das nie fotografiert wurde. Drei Werkzeuge:

  * shift_fill: Grundplatten haben ein regelmäßiges Noppengitter. Das Loch wird aus der Umgebung gefüllt, die um
    ganze Noppen versetzt ist – so passen Noppen, Licht und Perspektive. Das ist fast immer die beste Wahl.
  * inpaint / inpaint_full: glatte Füllung aus den Nachbarn (normierte Faltung). Für Tisch, Wand, kleine Reste.
  * Qwen-Clean-Plate (fal_api.py qwen): KI entfernt ein Objekt. Nur innerhalb der Lochmaske übernehmen, nie das
    ganze Bild (Qwen verändert still Details außerhalb).

Das Gitter (row, col) als Pixelvektoren zweier Nachbarnoppen misst estimate_lattice() auf einem freien Stück Platte.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .core import grow_mask


def ncfill(val: np.ndarray, w: np.ndarray, sig: float) -> np.ndarray:
    """Normierte Faltung: glatter Wert aus den gewichteten Nachbarn."""
    return ndi.gaussian_filter(val * w, sig) / np.maximum(ndi.gaussian_filter(w, sig), 1e-4)


def inpaint(rgb: np.ndarray, valid: np.ndarray, fill: np.ndarray, sigmas=(3.0, 6.0, 12.0, 24.0)) -> np.ndarray:
    """Füllt fill aus den gültigen Nachbarpixeln (normierte Faltung, von fein nach grob)."""
    out = rgb.copy()
    todo = fill.copy()
    w = valid.astype(np.float32)
    for s in sigmas:
        if not todo.any():
            break
        den = ndi.gaussian_filter(w, s)
        num = ndi.gaussian_filter(rgb * w[..., None], (s, s, 0))
        ok = todo & (den > 0.05)
        out[ok] = num[ok] / den[ok][:, None]
        todo &= ~ok
    return out


def inpaint_full(rgb, valid, fill, sigmas=(2.0, 4.0, 8.0, 16.0, 32.0, 64.0)) -> np.ndarray:
    """Wie inpaint(), aber lückenlos: was zu weit weg liegt, bekommt den nächsten gültigen Nachbarn."""
    out = inpaint(rgb, valid, fill, sigmas)
    todo = fill.copy()
    w = valid.astype(np.float32)
    for s in sigmas:
        todo &= ~(ndi.gaussian_filter(w, s) > 0.05)
    if todo.any() and valid.any():
        _, (iy, ix) = ndi.distance_transform_edt(~valid, return_indices=True)
        out[todo] = rgb[iy[todo], ix[todo]]
    return out


def estimate_lattice(img: np.ndarray, box) -> tuple[tuple[float, float], tuple[float, float]]:
    """Misst das Noppengitter einer Grundplatte in box=(x0,y0,x1,y1) (freies Stück Platte, mind. ~6x6 Noppen).
    Gibt zwei Gittervektoren (row, col) in Pixeln zurück: row ~ entlang der Bildbreite, col ~ in die Tiefe."""
    x0, y0, x1, y1 = [int(v) for v in box]
    g = img[y0:y1, x0:x1].mean(axis=2) if img.ndim == 3 else img[y0:y1, x0:x1]
    g = g - ndi.gaussian_filter(g, 8)
    g = g * np.hanning(g.shape[0])[:, None] * np.hanning(g.shape[1])[None, :]
    F = np.fft.fft2(g)
    ac = np.fft.fftshift(np.fft.ifft2(np.abs(F) ** 2).real)
    cy, cx = ac.shape[0] // 2, ac.shape[1] // 2
    yy, xx = np.mgrid[0:ac.shape[0], 0:ac.shape[1]]
    r = np.hypot(yy - cy, xx - cx)
    ac[r < 6] = ac.min()
    peaks = (ac == ndi.maximum_filter(ac, size=5)) & (ac > 0.25 * ac.max())
    ys, xs = np.nonzero(peaks)
    vec = [(float(x - cx), float(y - cy)) for y, x in zip(ys, xs)]
    vec = [v for v in vec if np.hypot(*v) > 0]
    vec.sort(key=lambda v: np.hypot(*v))
    if not vec:
        raise ValueError("kein Gitter gefunden – größeres freies Plattenstück wählen")
    v1 = vec[0]
    v2 = None
    for v in vec[1:]:
        cross = abs(v1[0] * v[1] - v1[1] * v[0]) / (np.hypot(*v1) * np.hypot(*v))
        if cross > 0.5:
            v2 = v
            break
    if v2 is None:
        raise ValueError("nur eine Gitterrichtung gefunden – anderes Plattenstück wählen")
    # row = eher waagerecht, col = eher senkrecht; positive Richtung nach rechts bzw. unten
    row, col = (v1, v2) if abs(v1[0]) >= abs(v2[0]) else (v2, v1)
    if row[0] < 0:
        row = (-row[0], -row[1])
    if col[1] < 0:
        col = (-col[0], -col[1])
    return row, col


def shift_fill(I, hole, avoid, row, col, fine=3, ring_w=10, lat=None):
    """Füllt jedes Teilstück von hole aus der um ganze Noppen versetzten Umgebung (Gitter row/col, ±fine px
    nachgeführt), gewählt nach bester Übereinstimmung im Ring darum; tieffrequent an den Ring angeglichen.
    avoid = Pixel, die weder Spender noch Ring sein dürfen (die Figur selbst, Nachbarfiguren).
    lat = Liste der Versätze (a, b) in ganzen Noppen; Standard: seitlich zuerst, dann eine Reihe vor/zurück.
    Gibt (Bild, gefüllt-Maske) zurück; nicht Gefülltes mit inpaint() nacharbeiten."""
    out = I.copy()
    h, w = hole.shape
    lab, n = ndi.label(grow_mask(hole, 2))
    done = np.zeros((h, w), bool)
    if lat is None:
        lat = [(a, b) for b in (0, 1, -1) for a in (1, -1, 2, -2, 3, -3, 0) if (a, b) != (0, 0)]
    for k in range(1, n + 1):
        comp = lab == k
        ys, xs = np.nonzero(comp)
        ring = grow_mask(comp, ring_w) & ~comp & ~avoid
        if ring.sum() < 30:
            ring = grow_mask(comp, 2 * ring_w) & ~comp & ~avoid
        ry, rx = np.nonzero(ring)
        if len(ry) < 10:
            continue
        best = None
        for a, b in lat:
            bx, by = a * row[0] + b * col[0], a * row[1] + b * col[1]
            fn = fine + (2 if abs(a) + abs(b) >= 2 else 0)
            for dy in range(-fn, fn + 1):
                for dx in range(-fn, fn + 1):
                    sx, sy = int(round(bx + dx)), int(round(by + dy))
                    if min(xs.min(), rx.min()) + sx < 0 or max(xs.max(), rx.max()) + sx >= w:
                        continue
                    if min(ys.min(), ry.min()) + sy < 0 or max(ys.max(), ry.max()) + sy >= h:
                        continue
                    if avoid[ys + sy, xs + sx].mean() > 0.02:
                        continue
                    err = np.abs(I[ry, rx] - I[ry + sy, rx + sx]).mean()
                    if best is None or err < best[0]:
                        best = (err, sx, sy)
        if best is None:
            continue
        _, sx, sy = best
        src = np.zeros_like(I)
        ys0, ys1 = max(0, -sy), min(h, h - sy)
        xs0, xs1 = max(0, -sx), min(w, w - sx)
        src[ys0:ys1, xs0:xs1] = I[ys0 + sy:ys1 + sy, xs0 + sx:xs1 + sx]
        wgt = ring.astype(np.float32)
        corr = np.stack([ncfill((I - src)[..., c], wgt, 8.0) for c in range(3)], 2)
        out[comp] = (src + corr)[comp]
        done |= comp
    return out, done


def clean_plate(I: np.ndarray, hole: np.ndarray, avoid: np.ndarray, row=None, col=None) -> np.ndarray:
    """Bequemer Weg: Loch erst per Noppenversatz, Rest glatt füllen. Ohne Gitter nur glatt."""
    out = I.copy()
    done = np.zeros(hole.shape, bool)
    if row is not None and col is not None:
        out, done = shift_fill(I, hole, avoid, row, col)
    rest = hole & ~done
    if rest.any():
        valid = ~(grow_mask(hole, 2) | avoid)
        out = inpaint_full(out, valid, rest)
    return out
