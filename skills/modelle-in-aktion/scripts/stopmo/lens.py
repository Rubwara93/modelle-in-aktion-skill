"""Lupe / Blick durchs Glas – ein Übergang, der im Bild steckt (Figur hält eine Lupe, Fernrohr, Bullauge …).

Nur einsetzen, wenn das Modell selbst so ein Objekt hat. Dann ist es der stärkste Übergang des Films: die Kamera
fährt ins Glas, das Glas öffnet sich als Kreisblende auf die nächste Nahaufnahme, später schrumpft es wieder.

    inner = world.shoot(nah_box)                       # was im Glas zu sehen ist
    outer = C.gblur(world.shoot(tot_box), 16) * 0.6    # Umfeld: unscharf, abgedunkelt
    frame = L.lupe(inner, outer, (1050, 600), 459)
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .core import H, W

_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)


def lens_maps(center, R, mag=1.05, barrel=0.06, off=(0.0, 0.0)):
    """Koordinatenkarten für leichte Vergrößerung + Tonnenverzeichnung im Glas."""
    dx, dy = _XX - center[0], _YY - center[1]
    r = np.sqrt(dx * dx + dy * dy) / R
    k = (1.0 / mag) * (1 - barrel * np.clip(r, 0, 1.2) ** 2)
    return center[1] + dy * k - off[1], center[0] + dx * k - off[0]


def warp(img, maps, mode="nearest"):
    ys, xs = maps
    out = np.empty_like(img)
    for c in range(3):
        out[..., c] = ndi.map_coordinates(img[..., c], [ys, xs], order=1, mode=mode)
    return out


def lupe(inner, outer, center, rx, ry=None, ang=0.0, rim=None, ref_radius=459.0):
    """Blick durchs Glas (Ellipse oder Kreis): innen inner, außen outer, schwarzer Rand mit Glanzlicht und
    Innenschatten. rim = Randbreite in px (Standard: proportional zum Radius)."""
    ry = rx if ry is None else ry
    x, y = _XX - center[0], _YY - center[1]
    a = np.radians(ang)
    xr = x * np.cos(a) + y * np.sin(a)
    yr = -x * np.sin(a) + y * np.cos(a)
    q = np.sqrt((xr / rx) ** 2 + (yr / ry) ** 2) + 1e-6
    th = np.arctan2(yr / ry, xr / rx)
    rloc = np.sqrt((rx * np.cos(th)) ** 2 + (ry * np.sin(th)) ** 2)
    sd = (q - 1) * rloc  # vorzeichenbehafteter Abstand zum Glasrand (innen < 0)
    rm = 0.5 * (rx + ry)
    m = np.clip(0.75 - sd, 0, 1.5) / 1.5
    f = outer * (1 - m[..., None]) + inner * m[..., None]
    w = max(10.0, 26 * rm / ref_radius) if rim is None else rim
    ring = np.clip(1 - np.abs(sd - w / 2) / (w / 2), 0, 1) ** 0.35
    f = f * (1 - ring[..., None]) + np.array([16, 16, 18], np.float32) * ring[..., None]
    shade = np.clip(1 + sd / (0.08 * rm), 0, 1) * (sd < 0)
    f = f * (1 - 0.35 * shade[..., None])
    angs = np.arctan2(y, x)
    hl = np.clip(1 - np.abs(sd - w * 0.35) / (w * 0.18), 0, 1) * np.clip(np.cos(angs + 2.3) * 1.6 - 0.6, 0, 1)
    return f + (np.array([235, 235, 240], np.float32) - f) * (0.55 * hl)[..., None]


def glass_light(a, gamma=0.7, gain=1.08):
    """Die Lupe bündelt Licht: dunkle Motive im Glas etwas anheben."""
    return 255.0 * np.clip(np.clip(a, 0, 255) / 255.0, 0, 1) ** gamma * gain


def iris(inner, outer, center, r, feather=2.0):
    """Einfache Kreisblende ohne Glasrand (z. B. für ein Bullauge, das schon im Foto steckt)."""
    d = np.sqrt((_XX - center[0]) ** 2 + (_YY - center[1]) ** 2)
    m = np.clip((r - d) / feather + 0.5, 0, 1)[..., None]
    return outer * (1 - m) + inner * m
