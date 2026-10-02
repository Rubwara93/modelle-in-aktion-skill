# Rhythmus und Bildsprache

## Takt

- **Figuren und Grafik: 12 Bilder/s »on twos«.** Jede Pose steht zwei Ausgabebilder lang (24 fps). Das ist der Brickfilm-Look. `core.write` verdoppelt automatisch.
- **Kamera: auf Einsen.** Fahrten und Zooms machen auf jedem 12-fps-Bild einen Schritt. Sonst ruckelt die Fahrt doppelt.
- **Musik: 120 BPM.** Ein Schlag = 0,5 s = 6 Bilder, ein Achtel = 3 Bilder. Harte Schnitte, Landungen, Hero-Momente und Pops liegen auf Schlägen oder Achteln. Die Musik wird später auf genau diese Zeiten komponiert.
- **Standbilder** bekommen den Registrierungs-Jitter (±1 px) aus `look()`. Nur Grafik-Halte (Titel steht, alle Farben sind an) laufen ohne Jitter (`jitter_flags`).

## Aufbau des Films

| Segment | Dauer | Inhalt |
|---|---|---|
| Intro | 4,0 s | Gesamtaufnahme aller Modelle, Titel liegt auf dem Tisch, Steinreihe leuchtet Stein für Stein auf, Push zum ersten Modell |
| je Modell | 8,0 s | Standardrhythmus (unten) |
| Outro | 4,5 s | harter Schnitt auf dieselbe Gesamtaufnahme, Turm aus allen Steinen wächst, Schlusszeilen, Blende nach Schwarz |

Gesamtlänge = 8,5 s + 8 s × Anzahl Modelle (2 Modelle: 24,5 s, 5 Modelle: 48,5 s). Ab 7 Modellen auf 6 s je Modell kürzen (Totale kürzer, nur ein Beat am Ende). Bei 1–2 Modellen ist ein kurzer Film in Ordnung. Wer länger will, gibt jedem Modell 12 s mit zwei Nahaufnahmen (zwei Hero-Momente, dazwischen kurz die Totale).

## Formate und stumme Wiedergabe

- Ausgabe ist 16:9 (1920×1080). Das läuft auf LinkedIn, auf Beamern und auf Monitoren. Ein Hochformat (4:5) bringt der Skill nicht mit, weil Totalen der Modelle darin nicht funktionieren.
- Auf LinkedIn startet das Video stumm. Der Film muss ohne Ton verständlich sein: Hero-Momente sichtbar machen (deutlicher Hub, Pop des Steins in der Bauchbinde, kurzes Aufleuchten mit `core.glow`), Halte nach jeder Aktion, Bauchbinden lange genug stehen lassen (mind. 3 s).

**Alle Modelle bekommen denselben Rhythmus und ungefähr dieselbe Länge.** Die Gruppen vergleichen. Wenn ein Modell deutlich länger oder aufwendiger ist, fühlt sich eine andere Gruppe zurückgesetzt.

## Standardrhythmus je Modell (96 Bilder)

```
i  0–3    Totale, Halt (Foto, nur Jitter)
i  4–17   Totale: Impuls – eine kleine Aktion, die die Hauptaktion ankündigt (Arm zeigt, Kette von Hüpfern)
i 18–23   Push-in um den Fixpunkt (6 Stufen, ease)                       Luft 1,5 s
i 24–71   Nahaufnahme: Aufbau – Hero-Aktion (auf einem Schlag) – Nachfedern – Halt
i 72–77   Zoom raus um denselben Fixpunkt (6 Stufen)                      Luft 6,0 s
i 78–95   Totale: ein bis zwei gemeinsame Beats (7,0 s und 7,5 s), Schlusshalt
```

**Immer erst das Gesamtbild, dann hinein, dann wieder heraus.** Ohne Totale erkennt die Gruppe ihr Modell nicht wieder (das war die erste Rückmeldung zu einem Film, der nur Nahaufnahmen hatte).

## Bewegung einer Figur (Stop-Motion-Grammatik)

- **Hüpfer:** Ausholen (1 Bild in die Knie, optional) → 2–3 Bilder Luft (Hub 60 % / 100 % / 70 %) → Landung. Hub etwa 0,4 Kopfhöhen. Kontaktschatten bleibt am Boden.
- **Nachfedern** nach einer großen Bewegung: Größe 100 → 92 → 100 % über 2 Bilder.
- **Kopf-Schnapp** oder Armklick: 1–2 Bilder, dann Halt. Mit einem trockenen Klick-Geräusch.
- **Halte sind Teil der Bewegung.** Nach jeder Aktion 3–6 Bilder Stillstand, damit das Auge folgt.
- **Gemeinsamer Beat:** Mehrere Figuren tun auf demselben Bild dasselbe (alle ziehen, alle hüpfen). Das ist der stärkste Ausdruck für »wir«.
- **Impulskette:** Figuren reagieren nacheinander im Abstand von 1 Bild (Domino). Gut für Verbundenheit.
- **Hero** genau einmal pro Modell, auf einem Schlag. In diesem Bild poppt der Stein in der Bauchbinde (`hero_t`).

## Kamera

- Totale: ganzes Modell mit Rand, keine Nachbarplatten, keine Personen, keine Holzhände oder Kärtchen (sonst entfernen, siehe ki-bewegung.md, oder Ausschnitt anpassen).
- Nahaufnahme: mindestens ~1200 Fotopixel breit, sonst wird es weich (Hochrechnen > 1,6 vermeiden).
- Hauptaktion **nicht oben links** (dort liegt die Bauchbinde, ca. x 40–1000, y 30–260).
- Push-in und Zoom raus mit `camera.zoom_path` um den gemeinsamen Fixpunkt. Kein Orbit, kein Schwenk um das Modell: KI-Kamerafahrten verbiegen Grundplatten.
- Harte Schnitte auf Schläge. Optische Übergänge nur, wenn sie im Bild stecken (durch eine Lupe, ein Fernrohr, ein Fenster schauen: `lens.lupe`).

## Einblendungen

- Bauchbinde oben links, fährt in 2 Bildern herein (`build_final.py` macht das), verschwindet kurz vor Szenenende. In der letzten Modellszene vor dem Outro bleibt sie stehen (`card_stays`), sonst blitzt darunter etwas auf.
- Claim höchstens zwei Zeilen, ausgewogen umbrochen. Karte höchstens halbe Bildbreite.
- Titel und Schlussblock liegen »tischfest« auf einer freien Tischfläche der Gesamtaufnahme. Position je Projekt setzen (`TITLE_AT`, `BLOCK_AT`) und im Kontaktbogen prüfen: kein Text über Modellen, nichts angeschnitten.
