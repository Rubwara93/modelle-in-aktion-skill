#!/usr/bin/env python3
"""Endschnitt: fertige Segmente aneinander, Bauchbinden im Stop-Motion-Takt, Musik + Geräusche gemischt, Lautheit.

Aufruf im Projektordner:
    python3 <skill>/scripts/build_final.py [--music audio/musik.mp3] [--out output/film.mp4] [--no-audio]

Liest project.json (Modelle, Theme, audio) und plan/segments.json:
{
  "order": ["intro", "modell-1", …, "outro"],
  "segments": {
    "modell-1": {
      "video": "segments/modell-1.mp4",   # 12-fps-Takt mit Look, aus dem Segment-Skript
      "duration_s": 8.0,
      "model": 0,                          # Index in project.json models -> Bauchbinde; fehlt = keine Karte
      "hero_t": 4.5,                       # Segmentzeit des Hero-Schlags (Baustein in der Karte poppt)
      "card_in_s": 0.25, "card_out_s": 5.9, "card_stays": false,
      "cues": [{"name": "hop-1", "t_s": 1.17, "gain": 0.8, "hit": true}, …]
    }, …
  }
}
Cues: Datei audio/sfx/<name>.mp3; t_s = Segmentzeit des Ereignisses (Landung, Klick). hit=true: nur der Anschlag
(120 ms) wird genommen und exakt aufs Bild gelegt; soft=true: weiche Geräusche nach Beginn statt Spitze ausrichten.
gain relativ zu -3 dBFS Spitze. pitch_semitones optional.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stopmo.overlays import Theme  # noqa: E402

W, H, STEP = 1920, 1080, 12
CARD_X, CARD_Y = 44, 36


def card_plan(order, segs, starts):
    """{12-fps-Bild: (modellindex, x-Versatz, pop)} – Karte fährt in 2 Bildern herein und in 2 Bildern hinaus."""
    plan = {}
    for k in order:
        s = segs[k]
        if s.get("model") is None:
            continue
        s0 = int(round(starts[k] * STEP))
        s1 = int(round((starts[k] + s["duration_s"]) * STEP))
        inn = s0 + max(2, int(round(float(s.get("card_in_s", 0.25)) * STEP)))
        stays = bool(s.get("card_stays"))
        out = s0 + int(round(float(s.get("card_out_s", s["duration_s"] - 0.25)) * STEP))
        hero = int(round((starts[k] + float(s.get("hero_t", -99))) * STEP))
        for f in range(inn, s1):
            if f == inn:
                x = -420
            elif f == inn + 1:
                x = 8
            elif not stays and f == out:
                x = -60
            elif not stays and f == out + 1:
                x = -720
            elif not stays and f > out + 1:
                continue
            else:
                x = 0
            pop = 1.18 if f == hero else (1.06 if f == hero + 1 else 1.0)
            plan[f] = (int(s["model"]), x, pop)
    return plan


def render_picture(order, segs, starts, total, theme, silent):
    n = int(round(total * STEP))
    plan = card_plan(order, segs, starts)
    concat = Path("work/_concat.txt")
    concat.parent.mkdir(parents=True, exist_ok=True)
    concat.write_text("".join(f"file '{os.path.abspath(segs[k]['video'])}'\n" for k in order))
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
                            "-vf", f"fps={STEP}:round=near,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-framerate", str(STEP), "-i", "-", "-vf", "fps=24", "-c:v", "libx264", "-crf", "17",
                            "-preset", "slow", "-profile:v", "high", "-level", "4.1", "-maxrate", "25M",
                            "-bufsize", "50M", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries",
                            "bt709", "-color_trc", "bt709", silent], stdin=subprocess.PIPE)
    cards = {}
    size = W * H * 3
    for f in range(n):
        buf = dec.stdout.read(size)
        if len(buf) < size:
            print(f"Warnung: nur {f} von {n} Bildern dekodiert (Segmentlängen in segments.json prüfen)")
            break
        if f in plan:
            idx, x, pop = plan[f]
            if (idx, pop) not in cards:
                cards[(idx, pop)] = theme.card(idx, pop)
            im = Image.frombuffer("RGB", (W, H), buf).convert("RGBA")
            im.alpha_composite(cards[(idx, pop)], (max(-2000, CARD_X + x - 20), CARD_Y - 20))
            buf = im.convert("RGB").tobytes()
        enc.stdin.write(buf)
    enc.stdin.close()
    enc.wait()
    dec.wait()


def analyse(path, thresh=0.6):
    """Spitze (dBFS) und Hauptanschlag (s) einer Geräuschdatei."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "48000", "-af",
                          "highpass=f=100,lowpass=f=9000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.abs(np.frombuffer(raw, np.float32))
    if len(x) == 0 or x.max() <= 0:
        return -90.0, 0.0
    peak = float(x.max())
    return 20 * np.log10(peak), int(np.argmax(x > thresh * peak)) / 48000


def mix(order, segs, starts, total, music, silent, out, audio_cfg):
    inputs, fc, fx = ["-i", silent], [], []
    n = 1
    if music:
        inputs += ["-i", music]
        n = 2
    for k in order:
        for cue in segs[k].get("cues", []):
            f = f"audio/sfx/{cue['name']}.mp3"
            if not os.path.exists(f):
                print(f"fehlt: {f}")
                continue
            gain = float(cue.get("gain", 0.8))
            if gain <= 0:
                continue
            inputs += ["-i", f]
            peak_db, onset = analyse(f, 0.25 if cue.get("soft") else 0.6)
            norm = gain * 10 ** ((-3 - peak_db) / 20)
            at = max(0, int(round((starts[k] + float(cue["t_s"]) - onset) * 1000)))
            ps = float(cue.get("pitch_semitones", 0) or 0)
            chain = f"[{n}:a]"
            if cue.get("hit"):
                chain += (f"atrim=start={max(0, onset - 0.005):.3f}:end={onset + 0.12:.3f},asetpts=PTS-STARTPTS,"
                          f"afade=out:st=0.09:d=0.035,")
                at = max(0, int(round((starts[k] + float(cue["t_s"])) * 1000)) - 5)
            chain += f"asetrate=44100*{2 ** (ps / 12):.5f},aresample=48000," if ps else "aresample=48000,"
            chain += f"highpass=f=100,lowpass=f=9000,volume={norm:.3f},adelay={at}|{at},apad[fx{len(fx)}]"
            fc.append(chain)
            fx.append(f"[fx{len(fx)}]")
            n += 1
    lufs = float(audio_cfg.get("target_lufs", -14))
    mg = float(audio_cfg.get("music_gain", 0.5))
    parts = []
    if music:
        fc.append(f"[1:a]aresample=48000,atrim=0:{total:.3f},equalizer=f=3000:t=q:w=1:g=-2,volume={mg},"
                  f"afade=out:st={max(0, total - 1.3):.3f}:d=1.25[mus]")
    if fx:
        fc.append(f"{''.join(fx)}amix=inputs={len(fx)}:normalize=0:dropout_transition=0,atrim=0:{total:.3f},"
                  f"volume=0.7[fol]")
    if music and fx:
        fc.append("[fol]asplit=2[fol1][folsc]")
        fc.append("[mus][folsc]sidechaincompress=threshold=0.015:ratio=4:attack=2:release=100[musd]")
        pre = "[musd][fol1]amix=inputs=2:normalize=0"
    elif music:
        pre = "[mus]anull"
    elif fx:
        pre = "[fol]anull"
    else:
        print("kein Ton (weder Musik noch Geräusche) – Film bleibt stumm")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-c", "copy", "-map_metadata", "-1",
                        "-movflags", "+faststart", out], check=True)
        return 0
    pre += ",alimiter=limit=0.89:level=false:latency=1"
    tp = -2.5  # AAC erzeugt bis ~+1,7 dB Überschwinger; so bleibt die Spitze unter -1 dBTP
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex",
                           ";".join(fc + [pre + f",loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json[aout]"]),
                           "-map", "[aout]", "-f", "null", "-"], capture_output=True, text=True)
    txt = meas.stderr[meas.stderr.rfind("{"):meas.stderr.rfind("}") + 1]
    m = json.loads(txt)
    ln = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    fc.append(pre + "," + ln + "[aout]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "0:v",
                    "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-t", f"{total:.3f}", "-map_metadata", "-1", "-movflags", "+faststart", out], check=True)
    return len(fx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--music", default=None)
    ap.add_argument("--out", default="output/film.mp4")
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args()
    cfg = json.loads(Path("project.json").read_text())
    plan = json.loads(Path("plan/segments.json").read_text())
    order, segs = plan["order"], plan["segments"]
    starts, t = {}, 0.0
    for k in order:
        if not Path(segs[k]["video"]).exists():
            sys.exit(f"Segment fehlt: {segs[k]['video']}")
        starts[k] = t
        t += float(segs[k]["duration_s"])
    total = t
    print(f"Gesamtdauer {total:.2f} s, {int(round(total * STEP))} Bilder à 1/12 s")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    silent = "work/_bild.mp4"
    render_picture(order, segs, starts, total, Theme.load("project.json"), silent)
    music = None if a.no_audio else (a.music or cfg.get("audio", {}).get("music"))
    if music and not Path(music).exists():
        sys.exit(f"Musikdatei fehlt: {music}")
    nfx = 0 if a.no_audio else mix(order, segs, starts, total, music, silent, a.out, cfg.get("audio", {}))
    if a.no_audio:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-c", "copy", "-map_metadata", "-1",
                        "-movflags", "+faststart", a.out], check=True)
    print(f"{a.out}: {total:.2f} s, {nfx} Geräusche")


if __name__ == "__main__":
    main()
