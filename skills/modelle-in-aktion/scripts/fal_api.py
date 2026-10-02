#!/usr/bin/env python3
"""KI-Aufrufe über fal.ai: Bewegung (Kling 3.0 Pro), Bildbearbeitung (Qwen), Musik und Geräusche (ElevenLabs).

Jede Person nutzt ihren EIGENEN fal.ai-Schlüssel (fal.ai -> Dashboard -> Keys) in der Umgebungsvariable FAL_KEY
oder in einer Datei .env im Projektordner (Zeile FAL_KEY=...). Der Schlüssel wird nie ausgegeben oder gespeichert.
Bilder werden über den fal-Speicher hochgeladen (kein eigener Server nötig).

Aufrufe (alle kosten Geld, Preise Stand 10/2026 – vor großen Läufen auf fal.ai prüfen):
  fal_api.py kling  <start.jpg> <prompt.txt> <out.mp4> [--end end.jpg] [--duration 5] [--cfg 0.6]   ~0,11 $/s
  fal_api.py qwen   <bild.jpg> <anweisung.txt> <out.png> [--size 1920x1080]                       ~0,03 $/MP
  fal_api.py music  <plan.json> <out.mp3>                                                         ~0,60 $/Minute (angefangen)
  fal_api.py sfx    <out.mp3> <dauer_s> "<prompt>"                                                 ~0,002 $/s
  fal_api.py sfx-batch <cues.json> <ordner>   (je Eintrag name, duration_s, prompt; vorhandene Dateien werden übersprungen)
  fal_api.py check                            (prüft Schlüssel und Paket, kostet nichts)

Jeder Aufruf wird in <projekt>/logs/fal.jsonl protokolliert (Modell, Request-ID, Dauer, Ausgabe), ohne Schlüssel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KLING = os.environ.get("FAL_KLING_MODEL", "fal-ai/kling-video/v3/pro/image-to-video")
QWEN = os.environ.get("FAL_QWEN_MODEL", "fal-ai/qwen-image-edit-2511")
MUSIC = "fal-ai/elevenlabs/music"
SFX = "fal-ai/elevenlabs/sound-effects/v2"

QWEN_NEGATIVE = ("people, human hands, text, watermark, extra figures, duplicate objects, changed colors, "
                 "melted plastic, distorted geometry, warped baseplate, blurry")
KLING_NEGATIVE = ("morphing, melting, bending plastic, organic deformation, extra limbs, extra figures, new objects, "
                  "camera movement, zoom, blur, distortion, low quality")


def _load_key() -> None:
    if os.environ.get("FAL_KEY"):
        return
    for p in (Path.cwd() / ".env", Path.cwd().parent / ".env"):
        if p.exists():
            for line in p.read_text().splitlines():
                if line.strip().startswith("FAL_KEY="):
                    os.environ["FAL_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return
    sys.exit("FAL_KEY fehlt. Eigenen Schlüssel auf fal.ai anlegen und als Umgebungsvariable FAL_KEY setzen "
             "oder in die Datei .env im Projektordner schreiben (Anleitung: github.com/Rubwara93/modelle-in-aktion-skill).")


def _client():
    _load_key()
    try:
        import fal_client  # noqa: WPS433
    except ImportError:
        sys.exit("Python-Paket fehlt: pip install fal-client")
    return fal_client


def _log(entry: dict) -> None:
    Path("logs").mkdir(exist_ok=True)
    with open("logs/fal.jsonl", "a") as fh:
        fh.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}, ensure_ascii=False) + "\n")


def _upload(path: str) -> str:
    fal = _client()
    return fal.upload_file(path)


def _run(model: str, args: dict, label: str) -> dict:
    fal = _client()
    t0 = time.time()
    status = "error"
    try:
        def on_update(u):
            name = type(u).__name__
            if name == "InProgress":
                print(f"  {label}: läuft …", flush=True)
        res = fal.subscribe(model, arguments=args, with_logs=False, on_queue_update=on_update)
        status = "ok"
        return res
    except Exception as e:  # Fehlermeldung ohne Header/Schlüssel weitergeben
        msg = str(e)
        if "key" in msg.lower() and ("invalid" in msg.lower() or "unauthor" in msg.lower()):
            msg = "Schlüssel ungültig (FAL_KEY prüfen)."
        elif "balance" in msg.lower() or "credit" in msg.lower() or "402" in msg:
            msg = "Guthaben auf fal.ai reicht nicht (Billing aufladen)."
        status = f"error: {msg[:200]}"
        raise SystemExit(f"{label}: {msg[:400]}")
    finally:
        _log({"model": model, "label": label, "status": status, "seconds": round(time.time() - t0, 1)})


def _download(url: str, out: str) -> None:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as r, open(out, "wb") as fh:
        fh.write(r.read())


def _text(arg: str) -> str:
    p = Path(arg)
    return p.read_text().strip() if p.exists() else arg.strip()


# ---------------------------------------------------------------- Befehle
def kling(start: str, prompt: str, out: str, end: str | None = None, duration: int = 5, cfg: float = 0.6,
          negative: str | None = None) -> str:
    """Image-to-Video. Ohne Kamerabewegung prompten; der Clip wird später maskiert ins Foto gesetzt."""
    args = {
        "start_image_url": _upload(start),
        "prompt": _text(prompt),
        "duration": str(int(min(15, max(3, duration)))),
        "cfg_scale": float(cfg),
        "generate_audio": False,  # Ton kommt aus der eigenen Mischung; spart ~1/3 der Kosten
        "negative_prompt": negative or KLING_NEGATIVE,
    }
    if end:
        args["end_image_url"] = _upload(end)
    print(f"Kling: {Path(start).name} -> {out} ({args['duration']} s, cfg {cfg}, Endbild {'ja' if end else 'nein'}),"
          f" ca. {0.112 * int(args['duration']):.2f} $")
    res = _run(KLING, args, f"kling:{Path(out).stem}")
    _download(res["video"]["url"], out)
    _log({"model": KLING, "label": f"kling:{Path(out).stem}", "file": out, "start": start, "end": end,
          "prompt": args["prompt"], "duration": args["duration"], "cfg": cfg})
    print(f"fertig: {out}")
    return out


def qwen(image: str, instruction: str, out: str, size: str = "1920x1080", negative: str | None = None) -> str:
    """Bildbearbeitung (Objekt entfernen, Pose ändern, Zielbild bauen). Ergebnis nie ganz übernehmen, sondern nur in
    einer Box/Maske um die gewollte Änderung zurückkopieren (sprite.blend_mask_region)."""
    w, h = (int(v) for v in size.lower().split("x"))
    args = {
        "prompt": _text(instruction),
        "image_urls": [_upload(image)],
        "negative_prompt": negative or QWEN_NEGATIVE,
        "image_size": {"width": w, "height": h},
        "output_format": "png",
        "num_images": 1,
    }
    res = _run(QWEN, args, f"qwen:{Path(out).stem}")
    _download(res["images"][0]["url"], out)
    _log({"model": QWEN, "label": f"qwen:{Path(out).stem}", "file": out, "input": image, "prompt": args["prompt"]})
    print(f"fertig: {out}")
    return out


def music(plan_path: str, out: str) -> str:
    """Musik nach Kompositionsplan (Abschnitte mit exakten Dauern). Format siehe assets/music_plan_beispiel.json."""
    plan = json.loads(Path(plan_path).read_text())
    cp = plan["composition_plan"] if "composition_plan" in plan else plan
    for s in cp["sections"]:
        s.setdefault("lines", [])
        s.setdefault("negative_local_styles", [])
        s.setdefault("positive_local_styles", [])
    cp.setdefault("positive_global_styles", [])
    cp.setdefault("negative_global_styles", [])
    total = sum(s["duration_ms"] for s in cp["sections"]) / 1000
    print(f"Musik: {len(cp['sections'])} Abschnitte, {total:.1f} s, ca. {0.6 * max(1, -(-int(total) // 60)):.2f} $")
    args = {"composition_plan": cp, "respect_sections_durations": True, "force_instrumental": True,
            "output_format": "mp3_44100_192"}
    res = _run(MUSIC, args, f"music:{Path(out).stem}")
    _download(res["audio"]["url"], out)
    _log({"model": MUSIC, "label": f"music:{Path(out).stem}", "file": out, "plan": plan_path})
    print(f"fertig: {out}")
    return out


def sfx(out: str, duration: float, prompt: str, influence: float = 0.6) -> str:
    args = {"text": prompt, "duration_seconds": float(min(22, max(0.5, duration))), "prompt_influence": influence}
    res = _run(SFX, args, f"sfx:{Path(out).stem}")
    _download(res["audio"]["url"], out)
    return out


def sfx_batch(cues_path: str, folder: str) -> None:
    """Geräusche aus einer Liste [{name, duration_s, prompt}] – gleiche Prompts werden nur einmal erzeugt."""
    cues = json.loads(Path(cues_path).read_text())
    Path(folder).mkdir(parents=True, exist_ok=True)
    by_prompt: dict = {}
    for c in cues:
        if (Path(folder) / f"{c['name']}.mp3").exists():
            continue
        by_prompt.setdefault((round(float(c["duration_s"]), 2), c["prompt"]), []).append(c["name"])

    def gen(item):
        (dur, prompt), names = item
        h = Path(folder) / f"_u-{hashlib.sha1(f'{dur}|{prompt}'.encode()).hexdigest()[:10]}.mp3"
        if not h.exists():
            sfx(str(h), dur, prompt)
        for n in names:
            (Path(folder) / f"{n}.mp3").write_bytes(h.read_bytes())
        return f"ok {', '.join(names)}"

    if not by_prompt:
        print("alle Geräusche vorhanden")
        return
    print(f"{len(by_prompt)} Geräusche zu erzeugen (ca. {0.002 * sum(d for d, _ in by_prompt) :.2f} $)")
    with ThreadPoolExecutor(4) as ex:
        for line in ex.map(gen, by_prompt.items()):
            print(line)


def check() -> None:
    _client()
    print("fal-client installiert, FAL_KEY gesetzt (Wert wird nicht angezeigt).")
    print(f"Modelle: {KLING} | {QWEN} | {MUSIC} | {SFX}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kling")
    k.add_argument("start"), k.add_argument("prompt"), k.add_argument("out")
    k.add_argument("--end"), k.add_argument("--duration", type=int, default=5), k.add_argument("--cfg", type=float, default=0.6)
    k.add_argument("--negative")
    q = sub.add_parser("qwen")
    q.add_argument("image"), q.add_argument("instruction"), q.add_argument("out")
    q.add_argument("--size", default="1920x1080"), q.add_argument("--negative")
    m = sub.add_parser("music")
    m.add_argument("plan"), m.add_argument("out")
    s = sub.add_parser("sfx")
    s.add_argument("out"), s.add_argument("duration", type=float), s.add_argument("prompt")
    b = sub.add_parser("sfx-batch")
    b.add_argument("cues"), b.add_argument("folder")
    sub.add_parser("check")
    a = ap.parse_args()
    if a.cmd == "kling":
        kling(a.start, a.prompt, a.out, a.end, a.duration, a.cfg, a.negative)
    elif a.cmd == "qwen":
        qwen(a.image, a.instruction, a.out, a.size, a.negative)
    elif a.cmd == "music":
        music(a.plan, a.out)
    elif a.cmd == "sfx":
        sfx(a.out, a.duration, a.prompt)
    elif a.cmd == "sfx-batch":
        sfx_batch(a.cues, a.folder)
    else:
        check()


if __name__ == "__main__":
    main()
