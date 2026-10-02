"""Grundbausteine: Laden, Zeit, Masken, Ausrichtung, Compositing, Look, Ausgabe.

Idee des ganzen Stils: Das scharfe Foto ist die Grundebene. Bewegt wird nur, was sich bewegen soll (Sprite aus dem
Foto oder weich maskierte Region aus einem KI-Clip), und das im Stop-Motion-Takt von 12 Bildern/s (»on twos«).
Alles läuft in float32-RGB (0..255), Ausgabe 1920x1080, jedes 12-fps-Bild wird bei der Ausgabe verdoppelt (24 fps).

Typischer Ablauf in einem Segment-Skript:
    from stopmo import core as C
    base = C.load("work/model-a/nah.jpg")
    clip = C.Clip("clips/model-a-take1.mp4")
    m = C.ellipse_mask((960, 300), (180, 260), feather=24)
    keys = [(0, 3.9), (6, 3.9), (8, 2.0), (12, 0.0), (30, 0.0)]   # (Ausgabebild, Clip-Sekunde): rückwärts + Halte
    frames = []
    for i in range(C.n_frames(2.5)):
        f = base.copy()
        f = C.paste(f, C.color_match(clip.at(C.remap(keys, i)), base, m), m)
        frames.append(f)
    C.write(frames, "segments/model-a.mp4")          # Look + Takt + 24 fps
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from scipy import ndimage as ndi

W, H = 1920, 1080
STEP_FPS = 12  # Stop-Motion-Takt (»on twos«)
OUT_FPS = 24


# ---------- Laden ----------
def open_photo(path: str) -> Image.Image:
    """Foto mit korrekter Drehung (EXIF) als RGB."""
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def load(path: str, size=(W, H)) -> np.ndarray:
    im = open_photo(path)
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float32)


def to_img(a: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def save(a: np.ndarray, path: str, quality=92) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    to_img(a).save(path, quality=quality)


class Clip:
    """Alle Bilder eines Videos im Speicher, skaliert auf 1920x1080. at(t) liefert das nächstliegende Bild."""

    def __init__(self, path: str, size=(W, H)):
        self.path = path
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=r_frame_rate",
             "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip()
        num, den = probe.split("/")
        self.fps = float(num) / float(den)
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={size[0]}:{size[1]}:flags=lanczos",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        n = len(raw) // (size[0] * size[1] * 3)
        self.frames = np.frombuffer(raw, np.uint8).reshape(n, size[1], size[0], 3)
        self.duration = n / self.fps

    def __len__(self):
        return len(self.frames)

    def at(self, t: float) -> np.ndarray:
        i = int(round(max(0.0, min(t, self.duration - 1e-6)) * self.fps))
        return self.frames[min(i, len(self.frames) - 1)].astype(np.float32)

    def frame(self, i: int) -> np.ndarray:
        return self.frames[max(0, min(i, len(self.frames) - 1))].astype(np.float32)


# ---------- Zeit ----------
def n_frames(seconds: float) -> int:
    """Anzahl 12-fps-Bilder für eine Schnittdauer."""
    return int(round(seconds * STEP_FPS))


def t_of(i: int) -> float:
    """Segmentzeit (s) des 12-fps-Bildes i."""
    return i / STEP_FPS


def remap(keys: list[tuple[float, float]], i: float) -> float:
    """Stückweise lineare Zeitkurve: keys = [(ausgabebild, clipsekunde), ...] aufsteigend nach Ausgabebild.
    Gleiche Clipsekunde in zwei Keys = Halt. Fallende Clipsekunden = rückwärts."""
    if i <= keys[0][0]:
        return keys[0][1]
    for (i0, t0), (i1, t1) in zip(keys, keys[1:]):
        if i <= i1:
            u = (i - i0) / max(1e-9, i1 - i0)
            return t0 + (t1 - t0) * u
    return keys[-1][1]


def ease(u: float) -> float:
    """Smoothstep 0..1 (weich an, weich aus)."""
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def ease_in(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u


def ease_out(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) * (1 - u)


def lerp(a, b, u):
    if isinstance(a, (tuple, list)):
        return type(a)(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u


# ---------- Masken (float32 0..1, H x W) ----------
def _blur(m: Image.Image, feather: float) -> np.ndarray:
    if feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return np.asarray(m).astype(np.float32) / 255.0


def rect_mask(box, feather=12.0, size=(W, H)) -> np.ndarray:
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rectangle(box, fill=255)
    return _blur(m, feather)


def ellipse_mask(center, radii, feather=12.0, size=(W, H)) -> np.ndarray:
    cx, cy = center
    rx, ry = radii
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    return _blur(m, feather)


def poly_mask(points, feather=12.0, size=(W, H), ss=4) -> np.ndarray:
    """Polygonmaske, 4-fach überabgetastet (glatte Kanten auch ohne feather)."""
    m = Image.new("L", (size[0] * ss, size[1] * ss), 0)
    ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in points], fill=255)
    m = m.resize(size, Image.BOX)
    return _blur(m, feather)


def color_mask(img: np.ndarray, rgb, tol=60.0, box=None, feather=2.0, grow=0) -> np.ndarray:
    """Maske aller Pixel nahe einer Farbe (euklidisch), optional nur in box=(x0,y0,x1,y1)."""
    d = np.sqrt(((img - np.array(rgb, np.float32)) ** 2).sum(axis=2))
    m = (d < tol).astype(np.uint8) * 255
    if box is not None:
        keep = np.zeros_like(m)
        x0, y0, x1, y1 = [int(v) for v in box]
        keep[y0:y1, x0:x1] = m[y0:y1, x0:x1]
        m = keep
    if grow > 0:
        m = grow_mask(m > 127, grow).astype(np.uint8) * 255
    return _blur(Image.fromarray(m), feather)


def grow_mask(binary: np.ndarray, r: float) -> np.ndarray:
    """Binärmaske um r Pixel erweitern (schnell über Distanztransformation)."""
    if r <= 0:
        return binary
    return ndi.distance_transform_edt(~binary) <= r


def soft(binary: np.ndarray, blur=1.2, grow=0.0) -> np.ndarray:
    """Binärmaske -> weiche Maske 0..1."""
    b = grow_mask(binary, grow) if grow > 0 else binary
    return np.clip(ndi.gaussian_filter(b.astype(np.float32), blur), 0, 1)


def largest(binary: np.ndarray, keep=1) -> np.ndarray:
    """Nur die keep größten zusammenhängenden Flächen behalten."""
    lab, n = ndi.label(binary)
    if n <= keep:
        return binary
    sizes = ndi.sum(binary, lab, range(1, n + 1))
    best = 1 + np.argsort(sizes)[::-1][:keep]
    return np.isin(lab, best)


def diff_mask(a: np.ndarray, b: np.ndarray, thresh=18.0, grow=6, feather=6.0, box=None) -> np.ndarray:
    """Wo unterscheiden sich zwei Bilder? Isoliert bewegte Figuren aus einem Clip (Bild t gegen Startbild)."""
    d = np.abs(a - b).mean(axis=2)
    m = (d > thresh).astype(np.uint8) * 255
    if box is not None:
        keep = np.zeros_like(m)
        x0, y0, x1, y1 = [int(v) for v in box]
        keep[y0:y1, x0:x1] = m[y0:y1, x0:x1]
        m = keep
    b = ndi.binary_opening(m > 127, iterations=2)
    if grow > 0:
        b = grow_mask(b, grow)
    return _blur(Image.fromarray(b.astype(np.uint8) * 255), feather)


def union(*ms: np.ndarray) -> np.ndarray:
    return np.clip(np.maximum.reduce(ms), 0, 1)


# ---------- Ausrichtung ----------
def _gray(a):
    return a.mean(axis=2) if a.ndim == 3 else a


def phase_shift(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """Verschiebung (dx, dy), um b auf a zu legen, per Phasenkorrelation. Dritter Wert = Peak-Güte."""
    ga, gb = _gray(a), _gray(b)
    ga = (ga - ga.mean()) * np.hanning(ga.shape[0])[:, None] * np.hanning(ga.shape[1])[None, :]
    gb = (gb - gb.mean()) * np.hanning(gb.shape[0])[:, None] * np.hanning(gb.shape[1])[None, :]
    F = np.fft.fft2(ga) * np.conj(np.fft.fft2(gb))
    r = np.fft.ifft2(F / (np.abs(F) + 1e-6)).real
    y, x = np.unravel_index(np.argmax(r), r.shape)
    if y > r.shape[0] // 2:
        y -= r.shape[0]
    if x > r.shape[1] // 2:
        x -= r.shape[1]
    return float(x), float(y), float(r.max())


def scale_about(img: np.ndarray, s: float, center) -> np.ndarray:
    h, w = img.shape[:2]
    cx, cy = center
    a = 1 / s
    coeffs = (a, 0, cx - a * cx, 0, a, cy - a * cy)
    return np.asarray(to_img(img).transform((w, h), Image.AFFINE, coeffs, resample=Image.BICUBIC)).astype(np.float32)


def shift(img: np.ndarray, dx: float, dy: float) -> np.ndarray:
    return np.asarray(to_img(img).transform(img.shape[1::-1], Image.AFFINE, (1, 0, -dx, 0, 1, -dy),
                                            resample=Image.BICUBIC)).astype(np.float32)


def align(frame: np.ndarray, base: np.ndarray, box, scales=(1.0,), center=None) -> tuple[np.ndarray, tuple]:
    """Legt ein Clip-Bild per Zoom (aus scales) + Verschiebung auf das Foto. KI-Clips driften oft ein paar Pixel.
    box = statischer Bereich (x0,y0,x1,y1), in dem sich nichts bewegt. Gibt (ausgerichtetes Bild, (scale, dx, dy))."""
    x0, y0, x1, y1 = [int(v) for v in box]
    ref = base[y0:y1, x0:x1]
    best = None
    h, w = frame.shape[:2]
    for s in scales:
        f = frame if abs(s - 1) < 1e-6 else scale_about(frame, s, center or (w / 2, h / 2))
        dx, dy, q = phase_shift(ref, f[y0:y1, x0:x1])
        if best is None or q > best[3]:
            best = (s, dx, dy, q, f)
    s, dx, dy, q, f = best
    return shift(f, dx, dy), (s, dx, dy)


# ---------- Compositing ----------
def paste(base: np.ndarray, src: np.ndarray, mask: np.ndarray) -> np.ndarray:
    m = mask[..., None]
    return base * (1 - m) + src * m


def color_match(src: np.ndarray, ref: np.ndarray, mask: np.ndarray, ring: float = 30.0) -> np.ndarray:
    """Gleicht Mittelwert/Streuung je Kanal der Quelle an die Referenz an, gemessen in einem Ring um die Maske.
    Nötig, weil KI-Clips Farbe und Helligkeit leicht verschieben."""
    inner = mask > 0.5
    band = grow_mask(inner, ring) & ~inner
    if band.sum() < 50:
        return src
    out = src.copy()
    for c in range(3):
        s, r = src[..., c][band], ref[..., c][band]
        sm, ss, rm, rs = s.mean(), s.std() + 1e-3, r.mean(), r.std() + 1e-3
        k = max(0.8, min(1.25, rs / ss))
        out[..., c] = (src[..., c] - sm) * k + rm
    return out


def contact_shadow(mask: np.ndarray, dx=0, dy=6, blur=10, opacity=0.25) -> np.ndarray:
    h, w = mask.shape
    im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
    im = im.transform((w, h), Image.AFFINE, (1, 0, -dx, 0, 1, -dy)).filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im).astype(np.float32) / 255.0 * opacity


def darken(base: np.ndarray, shadow: np.ndarray) -> np.ndarray:
    return base * (1 - shadow[..., None])


def brighten(img: np.ndarray, mask: np.ndarray, gain=1.1, warm=0.0) -> np.ndarray:
    out = img * (1 + (gain - 1) * mask[..., None])
    if warm:
        out[..., 0] += warm * 255 * mask
        out[..., 2] -= warm * 255 * mask
    return out


def glow(img: np.ndarray, mask: np.ndarray, color=(255, 240, 210), strength=0.2, blur=18.0) -> np.ndarray:
    """Weiches Leuchten (Screen) – z. B. ein Herz, das aufglüht."""
    g = ndi.gaussian_filter(np.clip(mask, 0, 1), blur)[..., None] * np.array(color, np.float32) * strength
    return 255 - (255 - img) * (255 - g) / 255


def gblur(a: np.ndarray, r: float) -> np.ndarray:
    return ndi.gaussian_filter(a, (r, r, 0)) if r > 0 else a


def unsharp(rgb: np.ndarray, radius=2.0, amount=0.5) -> np.ndarray:
    """Nachschärfen, z. B. nach dem Hochrechnen eines kleinen Ausschnitts."""
    return rgb + amount * (rgb - ndi.gaussian_filter(rgb, (radius, radius, 0)))


def zoom(img: np.ndarray, factor: float, center=(W / 2, H / 2)) -> np.ndarray:
    """Digitaler Zoom (>=1) um einen Punkt, Bildgröße bleibt. Für große Zooms lieber camera.shoot() aus dem
    Originalfoto nehmen, das bleibt scharf."""
    if abs(factor - 1) < 1e-4:
        return img
    h, w = img.shape[:2]
    cx, cy = center
    zw, zh = w / factor, h / factor
    x0 = min(max(cx - zw / 2, 0), w - zw)
    y0 = min(max(cy - zh / 2, 0), h - zh)
    return np.asarray(to_img(img).resize((w, h), Image.LANCZOS, box=(x0, y0, x0 + zw, y0 + zh))).astype(np.float32)


# ---------- Look + Ausgabe ----------
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_VIGNETTE = (1 - 0.06 * np.clip(np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2) - 0.6, 0, 1))[..., None]
del _yy, _xx


def look(img: np.ndarray, i: int, jitter=True, grain=4.0, flicker=0.005, warm=True) -> np.ndarray:
    """Gemeinsamer Look: leicht warm, etwas Kontrast, Einzelbild-Flackern, feines Korn, ±1 px Registrierungs-Jitter.
    Der Jitter macht aus einem Standbild ein »fotografiertes« Stop-Motion-Bild."""
    rng = np.random.default_rng(1000 + i)
    out = img.copy()
    if warm:
        out[..., 0] *= 1.02
        out[..., 2] *= 0.975
    out = (out - 128) * 1.05 + 128  # Kontrast
    lum = out.mean(axis=2, keepdims=True)
    out = lum + (out - lum) * 1.06  # Sättigung
    out *= 1 + flicker * (rng.random() - 0.5) * 2
    if grain:
        out += rng.normal(0, grain, out.shape[:2])[..., None]
    if jitter:
        out = shift(out, rng.integers(-1, 2), rng.integers(-1, 2))
    out *= _VIGNETTE  # kaum sichtbar
    return np.clip(out, 0, 255)


def write(frames, out: str, apply_look=True, jitter_flags: list[bool] | None = None, audio: str | None = None,
          crf=14) -> str:
    """12-fps-Bilder -> MP4 in 24 fps (jedes Bild doppelt). frames darf eine Liste oder ein Generator sein.
    jitter_flags[i]=False für Bilder, die ruhig stehen müssen (z. B. Grafik-Halt)."""
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-framerate", str(STEP_FPS), "-i", "-"]
    if audio:
        cmd += ["-i", audio]
    cmd += ["-vf", f"fps={OUT_FPS}", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p"]
    cmd += (["-c:a", "aac", "-shortest"] if audio else ["-an"]) + [out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, f in enumerate(frames):
        if f.shape[:2] != (H, W):
            raise ValueError(f"Bild {i} hat {f.shape[1]}x{f.shape[0]}, erwartet {W}x{H}")
        j = True if jitter_flags is None else jitter_flags[i]
        g = look(f, i, jitter=j) if apply_look else f
        p.stdin.write(np.clip(g, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    if p.returncode:
        raise RuntimeError(f"ffmpeg-Fehler bei {out}")
    return out


def sheet(frames, out: str, cols=6, width=320, every=1) -> str:
    """Kontaktbogen zur Sichtprüfung (jedes n-te Bild, mit Bildnummer). Immer ansehen, bevor ein Segment als
    fertig gilt."""
    frames = list(frames)
    sel = list(range(0, len(frames), every))
    h = int(width * H / W)
    rows = math.ceil(len(sel) / cols)
    im = Image.new("RGB", (cols * width, rows * h), (20, 20, 20))
    d = ImageDraw.Draw(im)
    for k, i in enumerate(sel):
        t = to_img(frames[i]).resize((width, h), Image.LANCZOS)
        x, y = (k % cols) * width, (k // cols) * h
        im.paste(t, (x, y))
        d.rectangle([x + 2, y + 2, x + 34, y + 16], fill=(0, 0, 0))
        d.text((x + 6, y + 3), str(i), fill=(255, 255, 0))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=85)
    return out
