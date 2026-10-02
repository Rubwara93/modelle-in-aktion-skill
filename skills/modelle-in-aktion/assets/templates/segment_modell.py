"""Segment »{KEY}« – Vorlage für eine Modell-Szene im Standardrhythmus. Kopieren nach comp/{KEY}.py und anpassen.

Standardrhythmus (8,0 s = 96 Bilder à 1/12 s, siehe references/rhythmus.md):
  Totale      i 0–17    Gesamtbild des Modells, 0–3 Halt, ab 4 erste kleine Aktion (Impuls), 18–23 Push-in
  Nah         i 24–71   Nahaufnahme der Hauptfigur(en): Aufbau, Hero-Aktion (Schlag), Nachfedern, Halt
  Zoom raus   i 72–77   6 Stufen zurück um denselben Fixpunkt
  Totale      i 78–95   Gesamtbild mit ein bis zwei gemeinsamen Beats (z. B. Hüpfer auf 7,0 und 7,5 s)

BILDPLAN (vor dem Bauen ausfüllen; Zeiten = Segmentzeit, Geräusch je Ereignis):
  0–3    Totale, Halt
  4–5    …                                                             -> Klick 0,42 s
  18–23  Push-in (6 Stufen)                                              -> Luft 1,50 s
  …      Hero: …                                                         -> Tock 4,50 s (hero_t)
  72–77  Zoom raus                                                       -> Luft 6,00 s
  84     Beat 1 …                                                        -> 7,00 s
  90     Beat 2 …                                                        -> 7,50 s

Aufruf (im Projektordner): python3 comp/{KEY}.py [--only 0,24,59] [--sheet-only]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

SKILL = Path(os.environ.get("STOPMO_SKILL", Path.home() / ".claude/skills/modelle-in-aktion"))
sys.path.insert(0, str(SKILL / "scripts"))
from stopmo import camera as K  # noqa: E402
from stopmo import core as C  # noqa: E402
from stopmo import sprite as S  # noqa: E402

KEY = "{KEY}"
OUT = f"segments/{KEY}.mp4"
SHEET = f"sheets/{KEY}.jpg"

# ---------------------------------------------------------------- Quelle und Kamera (Fotopixel)
WORLD = K.World("input/{KEY}.jpg")          # oder bereinigtes Weltbild aus work/{KEY}/welt.jpg
TOT = WORLD.fit_box()                        # Gesamtbild: ganzes Modell, Platte vollständig, kein Nachbarmodell
NAH = K.box_around((2400, 2000), 1600)       # Nahaufnahme um die Hauptfigur (mind. 1200 px breit = scharf)
PUSH = K.zoom_path(TOT, NAH, 7, C.ease)[1:]  # 6 Stufen rein (Bild 18–23), landet exakt in NAH
PULL = list(reversed(K.zoom_path(TOT, NAH, 7, C.ease)))[1:]  # 6 Stufen raus (72–77)

# ---------------------------------------------------------------- Figuren (Weltkoordinaten)
# Hüpfer: Polygon eng um die Figur (photo_tools.py grid zum Ablesen), lmax = größter Hub in Fotopixeln,
# frames = {bild: hub} – mit S.hop_lifts(start, lmax) erzeugen. ROW/COL = Noppengitter (fill.estimate_lattice).
ROW, COL = None, None
HOPS = [
    # {"name": "figur-a", "poly": [(x, y), …], "lmax": 40, "frames": {**S.hop_lifts(84, 40), **S.hop_lifts(90, 40)}},
]

# Optionaler KI-Clip in der Nahaufnahme (fal_api.py kling, Startbild = photo_tools crop von NAH):
# keys = [(ausgabebild, clipsekunde)] – rückwärts abspielen, wenn Kling AUS der gebauten Pose heraus bewegt hat.
CLIP = None  # {"file": "clips/{KEY}-a.mp4", "mask_poly": [(x, y), …] (Bildkoordinaten der Nah), "keys": [(24, 3.9), (40, 3.9), (46, 0.0)], "align_box": (0, 700, 400, 1080)}

N = 96
HERO = 54           # Bild des Hero-Schlags (4,5 s)
CARD_IN, CARD_OUT = 0.25, 7.75


def camera(i: int):
    if i < 18:
        return TOT
    if i < 24:
        return PUSH[i - 18]
    if i < 72:
        return NAH
    if i < 78:
        return PULL[i - 72]
    return TOT


class Scene:
    def __init__(self):
        self.base = WORLD.array()
        self.hops = [(h, S.Hopper(self.base, h["poly"], h["lmax"], ROW, COL, name=h["name"])) for h in HOPS]
        self.clip = None
        if CLIP:
            self.clip = C.Clip(CLIP["file"])
            self.clip_mask = C.poly_mask(CLIP["mask_poly"], feather=10)
            self.nah_plate = WORLD.shoot(NAH)

    def frame(self, i: int) -> np.ndarray:
        box = camera(i)
        active = [(h, hop) for h, hop in self.hops if h["frames"].get(i, 0) > 0]
        if active:
            cv = self.base.copy()
            for h, hop in active:
                hop.render(cv, h["frames"][i])
            f = K.World(cv).shoot(box, cache=False)
        else:
            f = WORLD.shoot(box)
        if self.clip is not None and box == NAH:
            t = C.remap(CLIP["keys"], i)
            src = self.clip.at(t)
            if CLIP.get("align_box"):
                src, _ = C.align(src, self.nah_plate, CLIP["align_box"])
            f = C.paste(f, C.color_match(src, f, self.clip_mask), self.clip_mask)
        return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--sheet-only", action="store_true")
    a = ap.parse_args()
    sc = Scene()
    if a.only:
        for i in [int(v) for v in a.only.split(",")]:
            C.save(sc.frame(i), f"work/{KEY}/probe-{i:02d}.jpg")
            print(f"work/{KEY}/probe-{i:02d}.jpg")
        return
    frames = [sc.frame(i) for i in range(N)]
    C.sheet(frames, SHEET, cols=8, width=240)
    print(SHEET)
    if a.sheet_only:
        return
    C.write(frames, OUT)
    seg = Path("plan/segments.json")
    plan = json.loads(seg.read_text()) if seg.exists() else {"order": [], "segments": {}}
    entry = plan["segments"].setdefault(KEY, {})
    keys = [m["key"] for m in json.loads(Path("project.json").read_text())["models"]]
    entry.update({"model": keys.index(KEY) if KEY in keys else None, "video": OUT, "duration_s": N / C.STEP_FPS, "hero_t": HERO / C.STEP_FPS,
                  "card_in_s": CARD_IN, "card_out_s": CARD_OUT})
    entry.setdefault("cues", [])
    seg.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
    print(f"{OUT}: {N} Bilder, {N / C.STEP_FPS:.2f} s")


if __name__ == "__main__":
    main()
