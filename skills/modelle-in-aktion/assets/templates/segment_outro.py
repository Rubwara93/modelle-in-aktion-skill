"""Segment »outro« – Vorlage (4,5 s = 54 Bilder). Kopieren nach comp/outro.py und anpassen.

Vereint: harter Schnitt auf den Schlussschlag zurück in DIESELBE Totale wie im ersten Bild des Intros. Alle Modelle,
die einzeln zu sehen waren, stehen wieder beieinander. Auf der freien Fläche wächst ein Turm aus allen Steinen
(Klammer zum Intro: dort eine Reihe einzelner Steine, hier ein gemeinsamer Bau).
  0..    je Modell landet ein Stein auf dem Turm, alle 3 Bilder (Achtel), Pop 1 Bild
  +3     Textblock springt herein: Kopfzeile / Unterzeile / Absender (linke Kante bündig)
  bis 47 alles steht, Kamera-Pull-out 1,08 -> 1,00 bis Bild 17, danach Stativ
  48–53  Blende nach Schwarz in 6 Bildern, Musik klingt aus

Aufruf: python3 comp/outro.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PIL import Image

SKILL = Path(os.environ.get("STOPMO_SKILL", Path.home() / ".claude/skills/modelle-in-aktion"))
sys.path.insert(0, str(SKILL / "scripts"))
from stopmo import camera as K  # noqa: E402
from stopmo import core as C  # noqa: E402
from stopmo import overlays as O  # noqa: E402

CFG = json.loads(Path("project.json").read_text())
TH = O.Theme.load("project.json")
WORLD = K.World(CFG.get("overview_photo", "input/gesamt.jpg"))
BOX = WORLD.fit_box()                     # dieselbe Totale wie Intro-Bild 0
FOCUS = ((BOX[0] + BOX[2]) / 2, (BOX[1] + BOX[3]) / 2)
BLOCK_AT = (960, 820)                     # Bildmitte des Blocks (Turm + Text) – auf freie Tischfläche legen!
N = 54
n = len(TH.colors)
FILL = [3 * k for k in range(n)]
TEXT_AT = FILL[-1] + 3

o = CFG.get("outro", {})
HEAD = TH.runs_sprite(o.get("head", [["Gemeinsam gebaut.", "ink"]]), 78)
SUB = TH.text_sprite(o["sub"], "muted", 40, "SemiBold") if o.get("sub") else None
SIGN = TH.text_sprite(o["sign"], "muted", 28, "Bold") if o.get("sign") else None
TOWER_W = 120


def camera(i):
    z = 1.08 - 0.08 * C.ease(min(i, 17) / 17)
    return K.zoom_box(BOX, z, FOCUS)


def overlay(i, box):
    layer = Image.new("RGBA", (C.W, C.H), (0, 0, 0, 0))
    z = (BOX[2] - BOX[0]) / (box[2] - box[0])
    cx, cy = K.to_screen(K.to_photo(BLOCK_AT, BOX), box)
    lit = sum(1 for f in FILL if i >= f)
    pop_idx = max((k for k, f in enumerate(FILL) if 0 <= i - f < 2), default=-1)
    tw = TH.tower(TOWER_W, lit=lit, pop_idx=pop_idx, pop=1.16 if pop_idx >= 0 and i == FILL[pop_idx] else 1.0)
    # nur die bereits gelandeten Steine zeigen: Turm von unten aufbauen
    if lit:
        step = int(TOWER_W * 0.40)
        keep_h = TOWER_W + step * (lit - 1) + 40
        tw = tw.crop((0, tw.height - keep_h, tw.width, tw.height))
        text_w = max(HEAD.width, SUB.width if SUB else 0)
        x_left = cx - (tw.width + 30 + text_w) * z / 2
        O.place_left(layer, tw, x_left, cy + (TOWER_W * 0.5 - keep_h / 2 + 20) * z, z)
        s = O.pop_curve(i, TEXT_AT)
        if s:
            tx = x_left + (tw.width + 30) * z
            O.place_left(layer, HEAD, tx, cy - 55 * z, s * z)
            if SUB:
                O.place_left(layer, SUB, tx + 4 * z, cy + 15 * z, s * z)
            if SIGN:
                O.place_left(layer, SIGN, tx + 4 * z, cy + 65 * z, s * z)
    return layer


def main():
    frames = []
    for i in range(N):
        box = camera(i)
        f = O.composite(WORLD.shoot(box), overlay(i, box))
        if i >= 48:
            f = f * (1 - (i - 47) / 6)
        frames.append(f)
    C.sheet(frames, "sheets/outro.jpg", cols=9, width=213)
    C.write(frames, "segments/outro.mp4", jitter_flags=[i < 18 for i in range(N)])
    seg = Path("plan/segments.json")
    plan = json.loads(seg.read_text()) if seg.exists() else {"order": [], "segments": {}}
    plan["segments"].setdefault("outro", {}).update({"video": "segments/outro.mp4", "duration_s": N / 12, "model": None})
    plan["segments"]["outro"].setdefault("cues", [])
    seg.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
    print("segments/outro.mp4")


if __name__ == "__main__":
    main()
