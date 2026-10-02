---
name: modelle-in-aktion
description: Macht aus Fotos von Workshop-Modellen (gebaut mit Bausteinen, z. B. in LEGO® SERIOUS PLAY®-Workshops) einen kurzen Stop-Motion-Film im Brickfilm-Stil – echtes Foto wird lebendig, Figuren hüpfen und handeln passend zu dem, was die Gruppe gebaut und erzählt hat, mit Bauchbinden, Titel, Musik und Geräuschen. Nutze diesen Skill immer, wenn jemand Workshop-Modelle, Wertemodelle, Teammodelle oder Bausteinmodelle als Video nachbereiten, animieren oder „in Aktion“ zeigen will, ein Recap-/Opener-Video aus Modellfotos braucht, „Stop-Motion aus den Modellen“ oder „Brickfilm“ sagt, oder Fotos von Grundplatten mit Minifiguren schickt und ein Video möchte – auch ohne das Wort Skill.
---

# Modelle in Aktion

Aus den Fotos der Modelle eines Workshops entsteht ein Film von 25–60 Sekunden (8 s je Modell plus Intro und Outro), im Format 16:9: Gesamtbild aller Modelle mit Titel, dann jedes Modell einzeln (Totale → hinein → Hero-Moment → wieder heraus), zum Schluss alle zusammen. Der Look: **Das scharfe Foto ist die Grundebene, nur einzelne Figuren bewegen sich, im Stop-Motion-Takt von 12 Bildern/s.** KI (Kling über fal.ai) liefert Bewegung nur dort, wo Sprites aus dem Foto nicht reichen, und wird maskiert eingesetzt. Sie gestaltet nie das ganze Bild um.

Die Teilnehmenden kennen ihre Modelle. Ein Film, der Bewegungen erfindet, die nicht zur Bedeutung passen, oder ein Modell verändert, wirkt auf sie fremd. Deshalb gilt die Reihenfolge: **verstehen → planen → bauen → prüfen**.

## Was der Skill mitbringt

```
scripts/stopmo/      Python-Bibliothek: core (Masken, Look, Ausgabe), camera (Ausschnitte aus dem Originalfoto),
                     sprite (Figuren hüpfen/drehen/lehnen + Kontaktschatten), fill (freigelegte Platte füllen),
                     lens (Lupe/Kreisblende), overlays (Bauchbinde, Titel, Steinreihe, Turm)
scripts/init_project.py   Projektordner + project.json
scripts/photo_tools.py    Koordinatengitter, 16:9-Ausschnitte, Boxen prüfen, Schwärzen
scripts/fal_api.py        Kling (Bewegung), Qwen (Bildbearbeitung), Musik, Geräusche – eigener FAL_KEY
scripts/build_final.py    Endschnitt mit Bauchbinden, Mischung, Lautheit
scripts/check_film.py     Kontaktbögen, Dauer, Lautheit
assets/templates/         segment_intro.py, segment_modell.py, segment_outro.py (Startpunkte)
assets/music_plan_beispiel.json, assets/fonts/ (Nunito, OFL)
references/               regie.md, rhythmus.md, ki-bewegung.md, ton.md, fallen.md
```

Pfad zum Skill: in Segment-Skripten über `STOPMO_SKILL` (Standard `~/.claude/skills/modelle-in-aktion`). Befehle unten mit `<skill>` = diesem Ordner.

## Voraussetzungen prüfen (zu Beginn, kostet nichts)

```bash
python3 -c "import numpy, scipy, PIL; print('ok')"     # sonst: pip install numpy scipy pillow
ffmpeg -version | head -1                                # sonst: brew install ffmpeg / winget install ffmpeg
python3 <skill>/scripts/fal_api.py check                 # fal-client + eigener FAL_KEY (nur für KI-Teile)
```

Fehlt der fal-Schlüssel, erklär kurz: eigenes Konto auf fal.ai, Guthaben aufladen, Key in `.env` im Projektordner (`FAL_KEY=…`). Ohne Schlüssel geht alles außer KI-Clips, Qwen-Bearbeitungen, Musik und Geräuschen. Der Film entsteht dann aus Sprites, mit Musik, die die Person selbst mitbringt (lizenzfrei), oder stumm.

## Ablauf

### 1. Projekt anlegen und Material sichten
`python3 <skill>/scripts/init_project.py <ordner> --keys <kurzname-1> <kurzname-2> …` (ein Kurzname je Modell, z. B. `zukunft stolz`; die Fotos heißen dann `input/<kurzname>.jpg`). Fotos nach `input/` (je Modell + eine Gesamtaufnahme `input/gesamt.jpg`), Flipcharts und Notizen nach `private/`. Jedes Foto mit `photo_tools.py grid` ansehen, bei Details mit `--box` hineinzoomen. Für Intro und Outro je Modell die 16:9-Box in der Gesamtaufnahme notieren (`models[].overview_box`). Die erste ist das Ziel des Push im Intro. Behaupte nichts über ein Modell, das du nicht im Foto gesehen hast.

### 2. Verstehen: Interview und Analyse → `references/regie.md`
Kurzes Interview (Zweck, Erkennbarkeit der Organisation, Namen/Claims/Farben, Geschichte je Modell, Titel, Musikrichtung, Budget). Dann je Modell eine Spezifikation `plan/specs/<key>.json` mit Elementen, Metaphern, Belegen, Bewegungspotenzial, Geschichte, Shots, Geräuschen. Zwei Kritiken (Handwerk, Bedeutung). **Checkpoint:** die Geschichte je Modell in zwei, drei Sätzen der Person zeigen und das Okay einholen.

### 3. Planen → `references/rhythmus.md`
`project.json` füllen. Schnittplan: Intro 4 s, je Modell 8 s im Standardrhythmus, Outro 4,5 s, 120 BPM. Je Segment einen Bildplan (Bild → Aktion → Geräusch). **Checkpoint Kosten:** geschätzte KI-Kosten nennen (Kling ~0,11 $/s, Qwen ~0,06 $/Bild, Musik ~0,60 $ je Variante) und vor dem ersten bezahlten Aufruf bestätigen lassen.

### 4. Bilder vorbereiten
Je Modell: Totale (ohne Nachbarmodelle, Holzhände, Kärtchen, Personen), Nahaufnahme(n) als Ausschnitt aus dem Originalfoto. Störendes per Qwen entfernen und **nur in der Maske** zurückkopieren. Noppengitter neben jeder Figur messen, die sich bewegt (`fill.estimate_lattice`). Polygone der bewegten Figuren mit dem Gitterbild nachzeichnen und mit `photo_tools.py boxes` prüfen.

### 5. Bewegung beschaffen → `references/ki-bewegung.md`
Erst Sprites (kostenlos, am echtesten): Hüpfer, Ruck, Impulskette, gemeinsamer Beat. Kling nur für Posenwechsel, die ein Sprite nicht kann (Arm hebt sich, Figur steigt ein). Startbild = Ausschnitt, kurzer neutraler Prompt, statische Kamera, oft rückwärts verwenden. Jeden Clip als Kontaktbogen prüfen.

### 6. Segmente bauen
Vorlagen nach `comp/` kopieren (`{KEY}` ersetzen) und ausbauen: `comp/intro.py`, `comp/<key>.py` je Modell, `comp/outro.py`. Erst Probebilder (`--only 0,24,59,84`), dann ganz rendern. **Jeden Kontaktbogen in `sheets/` ansehen**: Figur verdoppelt, verbogen, Geist am alten Platz? Aktion unter der Bauchbinde? Text über Modellen? Die Skripte tragen Dauer, Hero und Bauchbinden-Zeiten in `plan/segments.json` ein. Reihenfolge `order` und `cues` ergänzt du.

### 7. Ton → `references/ton.md`
Musikplan auf die Segmentgrenzen, zwei Varianten, Person wählt. Geräusche je Ereignis aus den Bildplänen (`sfx-batch`), Cues mit Zeiten in `plan/segments.json`.

### 8. Endschnitt und Prüfung
`python3 <skill>/scripts/build_final.py --out output/<titel>.mp4`, dann `check_film.py`. Kontaktbögen ansehen, Lautheit prüfen (−14 LUFS Social, −16 LUFS Raum). Der Person zuerst eine Vorschau zeigen, Rückmeldungen gezielt pro Segment umsetzen (nur das betroffene Segment neu rendern, dann den Endschnitt).

## Regeln, die immer gelten

- **Keine Markennamen im Video**: weder Hersteller der Steine noch geschützte Methodennamen, kein Firmenname der Auftraggeber, wenn die Organisation nicht erkennbar sein soll. Auch im Bild prüfen (Kärtchen, Verpackungen, Kisten im Hintergrund). Was vertraulich ist, kommt auch nicht in die Dateimetadaten (`build_final.py` entfernt sie).
- **Personen schützen**: keine Gesichter, keine Namen, keine Flipchart-Zitate im Film. Flipcharts und Notizen werden nur lokal gelesen und nie hochgeladen.
- **Das Modell nicht verändern**: KI-Ergebnisse nur maskiert übernehmen. Keine neuen Objekte, keine Farbwechsel, keine Kamerafahrten, die Platten verbiegen.
- **Gleicher Rhythmus für alle Modelle**: Jede Gruppe soll ungefähr gleich viel Zeit und Zuwendung bekommen.
- **Kosten offenlegen**: vor bezahlten Aufrufen schätzen, jeden Aufruf protokolliert `fal_api.py` in `logs/fal.jsonl`.

Bekannte Fallen und ihre Lösungen: `references/fallen.md`. Lies die Datei, bevor du Segmente baust.

## Dateien im Projekt (Kurzform)

- `project.json`: `title.lines`, `outro.head/sub/sign` (+ `head_px/sub_px/sign_px`), `theme` (Farben, Schrift), `overview_photo`, `models[]` (`key`, `label`, `name`, `claim`, optional `claim_lines`, `color`, `photo`, `overview_box`), `audio` (`target_lufs`, `music_gain`, `music`).
- `plan/segments.json`: `order` und je Segment `video`, `duration_s`, `model` (Index oder null), `hero_t`, `card_in_s`, `card_out_s`, `card_stays`, `cues[]` (`name`, `t_s`, `gain`, `hit`/`soft`, `pitch_semitones`). Format siehe Kopf von `build_final.py`.
