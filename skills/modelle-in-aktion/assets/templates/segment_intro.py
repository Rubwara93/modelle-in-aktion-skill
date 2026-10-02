"""Segment »intro« – Vorlage (4,0 s = 48 Bilder). Kopieren nach comp/intro.py und anpassen.

Getrennt -> vereint: echtes Foto aller Modelle, der Titel liegt »tischfest« auf einer freien Fläche im Bild (er wird
mit der Kamera mitbewegt, gleitet also nicht über das Foto).
  0–2    Aufblende aus Schwarz
  6      Titelzeile 1 springt herein (0,5 s)
  12     Reihe grauer Bausteine springt herein (1,0 s)
  18     Titelzeile 2 in Akzentfarbe (1,5 s, Schlag)
  24..   je Modell leuchtet sein Stein in der Modellfarbe auf, Pop 115 % -> 97 % -> 100 % (Achtel: alle 3 Bilder)
  0–34   langsamer Push-in 1,00 -> 1,05, auf jedem Bild ein Schritt
  40–41  Grafik schrumpft in 2 Bildern zur Mitte und ist weg
  40–45  Push zum ersten Modell (Ease), 45–47 Halt -> harter Schnitt in dessen Totale

Aufruf: python3 comp/intro.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SKILL = Path(os.environ.get("STOPMO_SKILL", Path.home() / ".claude/skills/modelle-in-aktion"))
sys.path.insert(0, str(SKILL / "scripts"))
from stopmo import camera as K  # noqa: E402
from stopmo import core as C  # noqa: E402
from stopmo import overlays as O  # noqa: E402

CFG = json.loads(Path("project.json").read_text())
TH = O.Theme.load("project.json")
WORLD = K.World(CFG.get("overview_photo", "input/gesamt.jpg"))
BOX_A = WORLD.fit_box("bottom")                     # Totale aller Modelle; oben keine Personen, unten freie Tischfläche
FOCUS = ((BOX_A[0] + BOX_A[2]) / 2, (BOX_A[1] + BOX_A[3]) / 2)
BOX_A_END = K.zoom_box(BOX_A, 1.05, FOCUS)
# Endeinstellung = das erste Modell in der Gesamtaufnahme (project.json models[0].overview_box, 16:9-Box in Fotopixeln
# der Gesamtaufnahme, mit photo_tools.py grid ablesen). Ohne Angabe: Mitte, Zoom 1,55 – dann unbedingt setzen.
_first = CFG["models"][0].get("overview_box")
BOX_END = tuple(_first) if _first else K.zoom_box(BOX_A, 1.55, FOCUS)
TITLE_AT = (960, 820)                       # Bildposition (bei BOX_A) der Titelmitte – auf freie Fläche legen!
# Zeigt die Gesamtaufnahme mehr Modelle als der Film: Ausschnitt BOX_A auf die gezeigten Modelle legen, oder alle
# zeigen und nur die Steine der Film-Modelle aufleuchten lassen (die Steinreihe hat so viele Steine wie project.json).
N = 48
n_models = len(TH.colors)
LIGHT = [24 + 3 * k for k in range(n_models)]   # Bilder, in denen die Steine aufleuchten
assert LIGHT[-1] <= 37, "zu viele Modelle für 4 s: Abstand auf 2 Bilder senken oder Intro verlängern"

L1 = TH.runs_sprite([CFG["title"]["lines"][0]], 108)
L2 = TH.runs_sprite([CFG["title"]["lines"][1]], 108) if len(CFG["title"]["lines"]) > 1 else None


def camera(i):
    if i < 36:
        return K.zoom_box(BOX_A, 1.0 + 0.05 * min(i, 34) / 34, FOCUS)
    if i < 40:
        return BOX_A_END
    k = min(i, 45) - 39
    return K.lerp_box(BOX_A_END, BOX_END, C.ease(k / 6), WORLD.size)


def overlay(i, box) -> Image.Image:
    layer = Image.new("RGBA", (C.W, C.H), (0, 0, 0, 0))
    if i >= 42:
        return layer
    z = (BOX_A[2] - BOX_A[0]) / (box[2] - box[0])           # Grafik zoomt mit (tischfest)
    anchor = K.to_screen(K.to_photo(TITLE_AT, BOX_A), box)
    shrink = {40: 0.5, 41: 0.18}.get(i, 1.0)
    lit = sum(1 for f in LIGHT if i >= f)
    pop_idx = max((k for k, f in enumerate(LIGHT) if 0 <= i - f < 3), default=-1)
    pop = O.pop_curve(i, LIGHT[pop_idx]) if pop_idx >= 0 else 1.0
    s1, sr = O.pop_curve(i, 6), O.pop_curve(i, 12)
    s2 = O.pop_curve(i, 18) if L2 else 0
    sc = z * shrink
    row = TH.brick_row(lit, pop_idx=pop_idx, pop=pop)
    O.place(layer, row, (anchor[0], anchor[1] - 130 * sc), sr * sc)
    O.place(layer, L1, (anchor[0], anchor[1] - 10 * sc), s1 * sc)
    if L2:
        O.place(layer, L2, (anchor[0], anchor[1] + 100 * sc), s2 * sc)
    return layer


def main():
    frames, jit = [], []
    for i in range(N):
        box = camera(i)
        f = O.composite(WORLD.shoot(box), overlay(i, box))
        if i < 3:
            f = f * (i + 1) / 4
        frames.append(f)
        jit.append(i not in range(36, 40))
    C.sheet(frames, "sheets/intro.jpg", cols=8, width=240)
    C.write(frames, "segments/intro.mp4", jitter_flags=jit)
    seg = Path("plan/segments.json")
    plan = json.loads(seg.read_text()) if seg.exists() else {"order": [], "segments": {}}
    plan["segments"].setdefault("intro", {}).update({"video": "segments/intro.mp4", "duration_s": N / 12, "model": None})
    plan["segments"]["intro"].setdefault("cues", [])
    seg.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
    print("segments/intro.mp4")


if __name__ == "__main__":
    main()
