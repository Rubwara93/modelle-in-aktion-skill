#!/usr/bin/env python3
"""Legt einen Projektordner an und schreibt eine project.json als Startpunkt.

    python3 init_project.py <projektordner> [--models 5] [--title "Unsere Werte …" "in Aktion"]

Ordner:
  input/      Originalfotos (je Modell eins oder mehrere, dazu eine Gesamtaufnahme aller Modelle)
  private/    Flipcharts, Notizen, Transkripte – NUR lokal lesen, nie an KI-Dienste schicken, nie ins Video
  plan/       brief.md, specs/<modell>.json, edit_plan.json, segments.json, music_plan.json, cues.json
  work/       Zwischenbilder, Ausschnitte, Masken (darf jederzeit neu erzeugt werden)
  clips/      KI-Clips von fal.ai (kosten Geld – nicht löschen)
  segments/   gerenderte Segmente (12-fps-Takt, mit Look)
  sheets/     Kontaktbögen zur Sichtprüfung
  audio/      musik.mp3, sfx/<name>.mp3
  comp/       Segment-Skripte (eins je Segment)
  output/     fertiger Film
  logs/       fal.jsonl (Kosten-/Aufrufprotokoll)
"""
import argparse
import json
from pathlib import Path

PALETTE = ["#E7362C", "#2F6DB5", "#E0A024", "#3C9A5F", "#7A4F9E", "#E46F1E", "#1A9AA6", "#C2407A"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--models", type=int, default=5)
    ap.add_argument("--keys", nargs="+", help="eigene Kurznamen je Modell, z. B. zukunft stolz (statt modell-1 …)")
    ap.add_argument("--title", nargs="+", default=["Unsere Werte …", "in Aktion"])
    a = ap.parse_args()
    keys = a.keys or [f"modell-{i + 1}" for i in range(a.models)]
    root = Path(a.folder)
    for d in ["input", "private", "plan/specs", "work", "clips", "segments", "sheets", "audio/sfx", "comp",
              "output", "logs"]:
        (root / d).mkdir(parents=True, exist_ok=True)
    cfg_path = root / "project.json"
    if cfg_path.exists():
        print(f"{cfg_path} existiert schon – nicht überschrieben.")
    else:
        title = a.title + [""] * (2 - len(a.title))
        cfg = {
            "title": {"lines": [[title[0], "ink"], [title[1], "accent"]]},
            "outro": {"head": [["Gemeinsam gebaut. ", "ink"], ["Gemeinsam gelebt.", "accent"]],
                      "sub": "", "sign": "", "head_px": 96, "sub_px": 48, "sign_px": 36},
            "theme": {"font_family": "Nunito", "font_dir": None, "ink": "#231F20", "accent": "#E7362C",
                      "muted": "#504A46", "card_bg": "#FFFFFF"},
            "overview_photo": "input/gesamt.jpg",
            "models": [{"key": k, "label": "", "name": f"Modell {i + 1}", "claim": "",
                        "color": PALETTE[i % len(PALETTE)], "photo": f"input/{k}.jpg",
                        "overview_box": None}
                       for i, k in enumerate(keys)],
            "audio": {"target_lufs": -14, "music_gain": 0.5, "music": "audio/musik.mp3"},
            "budget_usd": 15,
        }
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
        print(f"angelegt: {cfg_path}")
    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text(".env\nprivate/\nwork/\nclips/\nsegments/\naudio/\noutput/\nlogs/\n")
    env = root / ".env.beispiel"
    if not env.exists():
        env.write_text("# Eigenen Schlüssel von fal.ai eintragen und Datei in .env umbenennen. Nie teilen.\nFAL_KEY=\n")
    print("Fertig. Fotos nach input/, Flipcharts/Notizen nach private/.")


if __name__ == "__main__":
    main()
