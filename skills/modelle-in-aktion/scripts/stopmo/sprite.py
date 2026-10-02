"""Figuren als Sprites aus dem Foto: freistellen, hüpfen, drehen, lehnen, mit Kontaktschatten absetzen.

Das ist das Herz des Stop-Motion-Looks ohne KI: Eine Minifigur ist starr. Sie bewegt sich in ganzen Posen
(Hüpfer, Drehung, Ruck), nie organisch. Ein Sprite aus dem scharfen Foto sieht deshalb echter aus als jede
KI-Animation. Die freigelegte Fläche darunter kommt aus fill.shift_fill (Noppenversatz).

    from stopmo import sprite as S, fill as F
    world = W.array()                                   # Foto als float32
    fig = S.Sprite.from_poly(world, POLY, keep=lambda I: I.mean(2) < 200)
    hop = S.Hopper(world, POLY, lmax=17, row=ROW, col=COL)
    for i, lift in enumerate([0, 0, 10, 17, 12, 0]):
        cv = hop.render(world.copy(), lift)
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from .core import grow_mask, to_img
from .fill import inpaint_full, ncfill, shift_fill


def pmask(points, box, ss=4) -> np.ndarray:
    """Weiche Polygonmaske (4-fach überabgetastet) im Ausschnitt box=(x0,y0,x1,y1) (ganze Zahlen)."""
    x0, y0, x1, y1 = [int(v) for v in box]
    m = Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    ImageDraw.Draw(m).polygon([((x - x0) * ss, (y - y0) * ss) for x, y in points], fill=255)
    return np.asarray(m.resize((x1 - x0, y1 - y0), Image.BOX)).astype(np.float32) / 255.0


def feet_of(alpha: np.ndarray, off=(0, 0), band=25) -> tuple[float, float]:
    """Fußpunkt: Mitte der untersten Pixelreihen der Figur."""
    ys, xs = np.nonzero(alpha > 0.5)
    ymax = ys.max()
    sel = ys > ymax - band
    return float(xs[sel].mean() + off[0]), float(ymax + off[1])


class Sprite:
    """Freigestellte Figur: RGB/Alpha im Ausschnitt (x0,y0 = Lage in der Quelle), Fußpunkt in Quellkoordinaten."""

    def __init__(self, rgb: np.ndarray, alpha: np.ndarray, name="", pad=6):
        ys, xs = np.nonzero(alpha > 0.01)
        h, w = alpha.shape
        self.x0, self.y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
        self.x1, self.y1 = min(w, xs.max() + pad + 1), min(h, ys.max() + pad + 1)
        self.rgb = rgb[self.y0:self.y1, self.x0:self.x1].copy()
        self.a = alpha[self.y0:self.y1, self.x0:self.x1].copy()
        self.foot = feet_of(alpha)
        self.name = name
        self.cap = None  # optional: Ankerpunkt (z. B. Kopf), der beim Bewegen mitgeführt wird

    @classmethod
    def raw(cls, rgb, a, x0, y0, foot, cap=None, name=""):
        s = cls.__new__(cls)
        s.rgb, s.a, s.x0, s.y0 = rgb, a, x0, y0
        s.y1, s.x1 = y0 + a.shape[0], x0 + a.shape[1]
        s.foot, s.cap, s.name = foot, cap, name
        return s

    @classmethod
    def from_poly(cls, img: np.ndarray, poly, keep=None, name="", feather=0.7) -> "Sprite":
        """Figur über ein von Hand gesetztes Polygon (Bildkoordinaten von img) freistellen. keep(I) -> bool-Array
        verfeinert die Maske auf echte Figurpixel (z. B. Farbe), damit kein Schatten-/Plattensaum mitkommt."""
        h, w = img.shape[:2]
        a = pmask(poly, (0, 0, w, h))
        if keep is not None:
            k = keep(img) & (a > 0.02)
            k = ndi.binary_fill_holes(ndi.binary_closing(k, iterations=2))
            k = ndi.binary_opening(k, iterations=1)
            a = np.clip(ndi.gaussian_filter(k.astype(np.float32), feather), 0, 1) * grow_mask(k, 1)
        return cls(img, a, name=name)

    def padded(self, p=90) -> "Sprite":
        """Rand ergänzen (Randfarbe nach außen fortgesetzt), damit Drehen keine schwarzen Säume erzeugt."""
        h, w = self.a.shape
        rgb = np.zeros((h + 2 * p, w + 2 * p, 3), np.float32)
        a = np.zeros((h + 2 * p, w + 2 * p), np.float32)
        rgb[p:p + h, p:p + w] = self.rgb
        a[p:p + h, p:p + w] = self.a
        _, (iy, ix) = ndi.distance_transform_edt(~(a > 0.02), return_indices=True)
        rgb = rgb[iy, ix]
        return Sprite.raw(rgb, a, self.x0 - p, self.y0 - p, self.foot, self.cap, self.name)

    def _M(self, scale, sy, angle):
        a = np.radians(angle)
        return np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]) @ np.diag([scale, scale * sy])

    def flipped(self) -> "Sprite":
        """Seitenverkehrt (Figur dreht sich um). Nur bei symmetrischen Figuren glaubwürdig."""
        fx = self.foot[0]
        rgb, a = self.rgb[:, ::-1].copy(), self.a[:, ::-1].copy()
        x0 = 2 * fx - self.x1
        return Sprite.raw(rgb, a, x0, self.y0, self.foot, self.cap, self.name + "_flip")

    def render(self, dst_foot, scale=1.0, sy=1.0, angle=0.0, size=None):
        """Sprite so transformieren, dass der Fußpunkt auf dst_foot liegt. Gibt (box, rgb, alpha) zurück."""
        fx, fy = self.foot
        dx, dy = dst_foot
        M = self._M(scale, sy, angle)
        Mi = np.linalg.inv(M)
        corners = np.array([[self.x0, self.y0], [self.x1, self.y0], [self.x0, self.y1], [self.x1, self.y1]], float)
        tc = (M @ (corners - [fx, fy]).T).T + [dx, dy]
        SW, SH = size if size else (10 ** 6, 10 ** 6)
        X0, Y0 = int(max(0, np.floor(tc[:, 0].min()) - 2)), int(max(0, np.floor(tc[:, 1].min()) - 2))
        X1, Y1 = int(min(SW, np.ceil(tc[:, 0].max()) + 2)), int(min(SH, np.ceil(tc[:, 1].max()) + 2))
        cst = Mi @ np.array([X0 - dx, Y0 - dy]) + np.array([fx - self.x0, fy - self.y0])
        coeffs = (Mi[0, 0], Mi[0, 1], cst[0], Mi[1, 0], Mi[1, 1], cst[1])
        sz = (max(1, X1 - X0), max(1, Y1 - Y0))
        rgb = np.asarray(to_img(self.rgb).transform(sz, Image.AFFINE, coeffs, resample=Image.BICUBIC)).astype(np.float32)
        al = Image.fromarray((np.clip(self.a, 0, 1) * 255).astype(np.uint8)).transform(sz, Image.AFFINE, coeffs,
                                                                                         resample=Image.BICUBIC)
        return (X0, Y0, X0 + sz[0], Y0 + sz[1]), rgb, np.asarray(al).astype(np.float32) / 255.0


def lean_back(spr: Sprite, d: float, waist_y: float, blend=12.0) -> Sprite:
    """Oberkörper (alles über waist_y, Quellkoordinaten) um d Pixel nach oben versetzen, Beine bleiben stehen.
    Liest sich in Aufsicht als Ruck nach hinten (»an einem Strang ziehen«)."""
    h, w = spr.a.shape
    ys = np.arange(h, dtype=np.float32) + spr.y0
    k = np.clip((waist_y + 4 - ys) / blend, 0, 1)
    src_y = (np.arange(h, dtype=np.float32) + d * k)[:, None].repeat(w, 1)
    src_x = np.arange(w, dtype=np.float32)[None, :].repeat(h, 0)
    rgb = np.stack([ndi.map_coordinates(spr.rgb[..., c], [src_y, src_x], order=1, mode="nearest") for c in range(3)], 2)
    a = ndi.map_coordinates(spr.a, [src_y, src_x], order=1, mode="constant", cval=0.0)
    cap = None if spr.cap is None else (spr.cap[0], spr.cap[1] - d)
    return Sprite.raw(rgb, a, spr.x0, spr.y0, spr.foot, cap, spr.name + "_lean")


def put(canvas: np.ndarray, spr: Sprite, foot, scale=1.0, sy=1.0, angle=0.0, lift=0.0, shadow=0.22, sblur=9.0,
        shadow_w=62.0, shadow_h=16.0, sdy=-6.0) -> np.ndarray:
    """Sprite auf die Leinwand (in place); lift = Höhe über dem Boden in Pixeln: Figur wandert hoch, der weiche
    Kontaktschatten bleibt am Boden und wird mit der Höhe größer und blasser. Ohne Schatten »schwebt« jede Figur."""
    H, W = canvas.shape[:2]
    box, rgb, al = spr.render((foot[0], foot[1] - lift), scale, sy, angle, size=(W, H))
    X0, Y0, X1, Y1 = box
    if shadow > 0:
        sw, shh = shadow_w * scale * (1 - 0.15 * min(max(lift, 0) / 60, 1)), shadow_h * scale
        cx, cy = foot[0] + 4, foot[1] + sdy
        bx0, by0 = int(max(0, cx - sw - 40)), int(max(0, cy - shh - 40))
        bx1, by1 = int(min(W, cx + sw + 40)), int(min(H, cy + shh + 40))
        if bx1 > bx0 and by1 > by0:
            yy, xx = np.mgrid[by0:by1, bx0:bx1]
            e = (((xx - cx) / sw) ** 2 + ((yy - cy) / shh) ** 2 <= 1).astype(np.float32)
            sh = ndi.gaussian_filter(e, sblur + min(max(lift, 0), 60) / 10) * shadow
            canvas[by0:by1, bx0:bx1] *= 1 - sh[..., None]
    rgb, al = rgb[:Y1 - Y0, :X1 - X0], al[:Y1 - Y0, :X1 - X0]
    reg = canvas[Y0:Y0 + al.shape[0], X0:X0 + al.shape[1]]
    canvas[Y0:Y0 + al.shape[0], X0:X0 + al.shape[1]] = reg * (1 - al[..., None]) + rgb * al[..., None]
    return canvas


def lift_rows(arr: np.ndarray, lift: float) -> np.ndarray:
    """arr um lift Pixel nach oben verschoben (Unterpixel, linear); unten wird nichts nachgeschoben."""
    h = arr.shape[0]
    sy = np.arange(h, dtype=np.float32) + lift
    i0 = np.clip(np.floor(sy).astype(int), 0, h - 1)
    i1 = np.clip(i0 + 1, 0, h - 1)
    f = (sy - np.floor(sy))[:, None]
    if arr.ndim == 3:
        f = f[..., None]
    out = arr[i0] * (1 - f) + arr[i1] * f
    out[sy > h - 1] = 0
    return out


class Hopper:
    """Starre Figur (Polygon im Weltbild), die senkrecht hüpft. Die Fläche, die beim Hub frei wird, kommt aus der
    um ganze Noppen versetzten Platte (row/col = Gittervektoren, siehe fill.estimate_lattice) oder – ohne Gitter –
    glatt aus der Umgebung. Kontaktschatten an den Füßen, schwächer je höher.

    poly        Umriss der Figur in Weltkoordinaten (von Hand nachgezeichnet, eng an der Figur)
    lmax        größter Hub in Weltpixeln (typisch: 0,4 Figurenkopf-Höhen)
    feet        Liste ((x, y), rx, ry) Schattenellipsen in Weltkoordinaten; None = automatisch am Fußpunkt
    avoid_polys Nachbarfiguren/Objekte, die nicht als Spender dienen dürfen
    keep        Funktion I -> bool, verfeinert die Polygonmaske auf echte Figurpixel
    """

    def __init__(self, world: np.ndarray, poly, lmax: float, row=None, col=None, feet=None, avoid_polys=(), keep=None,
                 name="", margin=110):
        xs, ys = [q[0] for q in poly], [q[1] for q in poly]
        Hh, Ww = world.shape[:2]
        x0, y0 = max(0, int(min(xs)) - margin), max(0, int(min(ys) - lmax) - margin)
        x1, y1 = min(Ww, int(max(xs)) + margin), min(Hh, int(max(ys)) + margin)
        self.box = (x0, y0, x1, y1)
        self.I = I = world[y0:y1, x0:x1].copy()
        self.a = pmask(poly, self.box)
        if keep is not None:
            k = keep(I) & (self.a > 0.02)
            k = ndi.binary_fill_holes(ndi.binary_closing(k, iterations=2))
            k = ndi.binary_opening(k, iterations=1)
            self.a = np.clip(ndi.gaussian_filter(k.astype(np.float32), 0.7), 0, 1) * grow_mask(k, 1)
        hull = self.a > 0.02
        L = int(np.ceil(lmax)) + 1
        cov = np.zeros_like(hull)
        cov[:-L] = hull[L:]
        E = grow_mask(hull & ~cov, 2)  # was beim größten Hub frei wird
        avoid = grow_mask(hull, 4)
        for q in avoid_polys:
            avoid |= grow_mask(pmask(q, self.box) > 0.02, 4)
        bg = I.copy()
        done = np.zeros_like(E)
        if row is not None and col is not None:
            # Spender: bevorzugt ganze Reihen darunter (dort liegt freie Platte), dann seitlich
            lat = [(a, b) for b in (2, 3, 1, -1) for a in (0, 1, -1, 2, -2, 3, -3)]
            sf, done = shift_fill(I, E, avoid, row, col, lat=lat)
            bg[done] = sf[done]
        rest = E & ~done
        if rest.any():
            bg = inpaint_full(bg, ~grow_mask(hull, 3) & ~avoid | done, rest)
        print(f"Hüpfer {name}: freigelegt {int(E.sum())} px, davon Noppenversatz {int((done & E).sum())} px")
        self.bg = bg
        self.E_a = np.clip(ndi.gaussian_filter(E.astype(np.float32), 0.8), 0, 1)
        if feet is None:
            fx, fy = feet_of(self.a)
            wid = max(8.0, (np.ptp(np.nonzero(hull.any(0))[0]) + 1) * 0.42)
            self.feet = [((fx, fy - 2), wid, wid * 0.28)]
        else:
            self.feet = [((fx - x0, fy - y0), rx, ry) for (fx, fy), rx, ry in feet]
        self._yy, self._xx = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(np.float32)
        self.lmax = lmax

    def render(self, cv: np.ndarray, lift: float, shadow=0.30) -> np.ndarray:
        """Figur mit Hub lift (Weltpixel) in cv (Weltbild, in place) zeichnen. lift <= 0: unverändert."""
        if lift <= 0:
            return cv
        x0, y0, x1, y1 = self.box
        R = cv[y0:y1, x0:x1]
        R = R * (1 - self.E_a[..., None]) + self.bg * self.E_a[..., None]
        for (fx, fy), rx, ry in self.feet:
            e = ((((self._xx - fx) / rx) ** 2 + ((self._yy - fy) / ry) ** 2) <= 1).astype(np.float32)
            op = shadow * (1 - 0.35 * min(lift / max(self.lmax, 1), 1.0))
            R = R * (1 - (ndi.gaussian_filter(e, 2.5 + lift / 5.0) * op)[..., None])
        a = lift_rows(self.a, lift)
        rgb = lift_rows(self.I, lift)
        R = R * (1 - a[..., None]) + rgb * a[..., None]
        cv[y0:y1, x0:x1] = R
        return cv


HOP_CURVE = (0.6, 1.0, 0.7)  # Hub-Anteile für 3 Luftbilder (ab, Scheitel, runter); Landung im 4. Bild auf 0


def hop_lifts(start: int, lmax: float, curve=HOP_CURVE) -> dict[int, float]:
    """Hubfahrplan {bild: hub} für einen Hüpfer ab Bild start (Landung = start + len(curve))."""
    return {start + k: lmax * c for k, c in enumerate(curve)}


def blend_mask_region(base: np.ndarray, edit: np.ndarray, box, feather=6.0) -> np.ndarray:
    """KI-Bearbeitung (z. B. Qwen) NUR in box zurückkopieren, weich überblendet. Der Rest bleibt Foto."""
    h, w = base.shape[:2]
    x0, y0, x1, y1 = [int(v) for v in box]
    m = np.zeros((h, w), np.float32)
    m[y0:y1, x0:x1] = 1
    m = np.clip(ndi.gaussian_filter(m, feather), 0, 1)
    return base * (1 - m[..., None]) + edit * m[..., None]


__all__ = ["Sprite", "Hopper", "put", "lean_back", "pmask", "feet_of", "lift_rows", "hop_lifts",
           "blend_mask_region", "ncfill"]
