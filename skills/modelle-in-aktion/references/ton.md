# Musik und Geräusche

## Musik (ElevenLabs Music über fal.ai)

Nie selbst synthetisieren (Sinus-, Zupf- oder Glockenklänge aus Code klingen nach Spieluhr oder Mittelalter). Immer ein Musikmodell mit Kompositionsplan.

1. **Plan bauen** (`plan/music_plan.json`, Vorlage `assets/music_plan_beispiel.json`): Abschnitte mit exakten Dauern in ms, die auf die Segmentgrenzen fallen: Intro 4000, je Modell 8000, Outro 4500. 120 BPM, 4/4. Ein Schlusstreffer genau auf dem Outro-Beginn.
2. **Stil**: instrumental, live gespielt, warm. Bewährt hat sich eine enge Funk-Soul-Rhythmusgruppe (trockenes Schlagzeug, runder E-Bass, gedämpfte Gitarre, kurze Klavier- und Bläserstiche). Negative Stile helfen mehr als positive: `glockenspiel, bells, celesta, music box, xylophone, ukulele, whistling, banjo, gang vocals, hey shouts, game show, ska, big band swing, high trumpet, lute, harp, recorder`.
3. **Zwei Varianten** erzeugen (je ~0,60 $), der Person beide vorspielen (Dateien schicken), wählen lassen. Musikgeschmack entscheidet die Person, nicht du.
4. Wenn ein Segment nachträglich länger wird: Musik nicht neu erzeugen, sondern einen Takt (2 s) per ffmpeg verdoppeln, Übergänge mit 10 ms Überblendung, und prüfen, dass der Schlusstreffer wieder auf dem Outro-Beginn liegt.

`python3 <skill>/scripts/fal_api.py music plan/music_plan.json audio/musik-a.mp3`

## Geräusche (ElevenLabs Sound Effects über fal.ai)

Ein Geräusch je sichtbarem Ereignis aus den Bildplänen: Landung, Klick, Hüpfer, Ruck, Glühen. Ohne Geräusch wirkt eine Landung weich.

- Prompts englisch, nah, trocken, Spielzeugmaßstab: »A single tiny dry plastic click of a toy figure arm rotating at the shoulder, very close, dry room«, »A small plastic toy figure landing on a studded plastic baseplate, one short crisp tock, close-up tabletop foley«. Dauer 0,5 s für Anschläge.
- Varianten über leicht andere Prompts oder `pitch_semitones` (±1–3), damit nicht jede Landung gleich klingt.
- `plan/cues.json` = Liste `{name, duration_s, prompt}` → `python3 <skill>/scripts/fal_api.py sfx-batch plan/cues.json audio/sfx`. Gleiche Prompts werden nur einmal erzeugt (~0,002 $/s, also Cent-Beträge).
- In `plan/segments.json` je Segment `cues`: `{name, t_s, gain, hit}`. `hit: true` für Anschläge (nur die ersten 120 ms, exakt aufs Bild gelegt), `soft: true` für weiche Flächen (Applaus, Glühen, Luft).

## Mischung (`build_final.py`)

- Geräusche auf −3 dBFS Spitze normiert, dann `gain`. Musik etwa −6 dB (`music_gain` 0,5), Sidechain-Ducking unter den Geräuschen.
- Lautheit: Social Media −14 LUFS (`audio.target_lufs`), Präsentation im Raum −16 LUFS. Spitze unter −1 dBTP.
- Läuft der Film ohne Ton (Endlosschleife auf Monitoren), muss er auch stumm funktionieren. Das tut er, wenn die Bewegungen klar und die Bauchbinden lesbar sind.
