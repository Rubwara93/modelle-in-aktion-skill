# Modelle in Aktion

Ein Skill für Claude Code, der aus Fotos von Workshop-Modellen einen kurzen Stop-Motion-Film macht. Gemeint sind Modelle, die Gruppen in Workshops mit Klemmbausteinen bauen. Grundlage bleibt das echte Foto, darin bewegen sich einzelne Figuren: Sie hüpfen, zeigen, steigen ein, ziehen gemeinsam an einem Strang. Jede Bewegung passt zu dem, was die Gruppe gebaut und erzählt hat. Dazu kommen Bauchbinden mit Namen und Claim je Modell, ein Titel, ein Schlussbild, Musik und Geräusche.

Typischer Einsatz: Nachbereitung eines Werte- oder Strategie-Workshops. Das Video läuft zum Auftakt des nächsten Treffens, in der Endlosschleife auf einem Monitor oder als Beispiel auf LinkedIn.

```
Intro (4 s)        alle Modelle, Titel liegt auf dem Tisch, Steine leuchten nacheinander auf
je Modell (8 s)    Totale → hinein → Hero-Moment → wieder heraus → gemeinsamer Beat
Outro (4,5 s)      alle Modelle, ein Turm aus allen Steinen wächst, Schlusszeilen
```

## Was du brauchst

- **Claude Code** (oder einen anderen Agenten, der das Agent-Skills-Format liest)
- **Python 3.10+** mit `numpy`, `scipy`, `pillow`, `fal-client`
- **ffmpeg**
- **Ein eigenes Konto bei [fal.ai](https://fal.ai)** mit etwas Guthaben, für KI-Bewegung, Bildbearbeitung, Musik und Geräusche. Jede Person nutzt ihren eigenen Schlüssel. Im Skill steckt kein Schlüssel, und niemand sonst bezahlt deine Aufrufe.
- **Gute Fotos**: je Modell ein scharfes Foto von schräg oben (Smartphone reicht, volle Auflösung), dazu eine Gesamtaufnahme aller Modelle mit etwas freier Tischfläche vorn. Der Skill funktioniert mit Modellen aus Klemmbausteinen jeder Art. Möglichst ohne Personen im Bild.

```bash
pip install numpy scipy pillow fal-client
brew install ffmpeg          # macOS; Windows: winget install ffmpeg
```

Den fal-Schlüssel legst du auf fal.ai unter *Dashboard → Keys* an. Er kommt in eine Datei `.env` im Projektordner:

```
FAL_KEY=dein-schluessel
```

Die Datei nie teilen und nie in ein Repository legen.

## Installation

**Claude Code**, als Plugin:

```
/plugin marketplace add Rubwara93/modelle-in-aktion-skill
/plugin install modelle-in-aktion@modelle-in-aktion
```

Oder von Hand:

```bash
git clone https://github.com/Rubwara93/modelle-in-aktion-skill.git
cp -r modelle-in-aktion-skill/skills/modelle-in-aktion ~/.claude/skills/
```

## Benutzung

```
Ich habe gestern einen Werte-Workshop gemacht, fünf Gruppen haben je ein Modell gebaut.
Die Fotos liegen in ~/Desktop/werte-workshop/fotos, die Flipcharts in ~/Desktop/werte-workshop/flipcharts.
Mach daraus einen Film wie „Unsere Werte … in Aktion“, ohne den Firmennamen, für LinkedIn.
```

Claude legt einen Projektordner an, sieht sich die Fotos genau an und fragt nach, was jedes Modell bedeutet. Dann schlägt Claude je Modell eine kleine Geschichte vor und holt dein Okay ein. Bevor etwas Geld kostet, nennt Claude die geschätzten Kosten. Danach entstehen die Szenen einzeln, du siehst Kontaktbögen und eine Vorschau, und am Ende steht der fertige Film in `output/`.

## Kosten (Stand Oktober 2026, Preise von fal.ai)

| Posten | Preis | typisch für 5 Modelle |
|---|---|---|
| KI-Bewegung (Kling 3.0 Pro, ohne Ton) | ~0,11 $ je Sekunde | 5–10 Clips à 5 s, also 3–6 $ |
| Bildbearbeitung (Qwen Image Edit) | ~0,06 $ je Bild | 10–20 Bilder, also 0,60–1,20 $ |
| Musik (ElevenLabs Music) | ~0,60 $ je angefangene Minute | 2 Varianten, also 1,20 $ |
| Geräusche (ElevenLabs Sound Effects) | ~0,002 $ je Sekunde | unter 0,20 $ |

Mit ein paar Wiederholungen kostet ein Film für fünf Modelle meist **5–10 $**. Ohne fal-Schlüssel geht es auch: Dann bewegen sich die Figuren nur als Ausschnitte aus dem Foto, und die Musik bringst du selbst mit (lizenzfrei) oder der Film bleibt stumm.

## Datenschutz

- Flipcharts, Mitschriften und Transkripte liest Claude nur auf deinem Rechner. Sie werden nie hochgeladen und kommen nie ins Video.
- An fal.ai gehen nur Ausschnitte der Modelle, ohne Personen, Gesichter und Namen.
- Der fertige Film enthält keine Metadaten wie Titel oder Autor.
- Ob die Organisation im Film erkennbar sein darf, entscheidest du. Ohne Freigabe der Teilnehmenden gehört kein Firmenname und kein Name einer Person ins Video.

## Wie es gebaut ist

Der Skill bringt eine kleine Python-Bibliothek mit (`skills/modelle-in-aktion/scripts/stopmo`). Sie enthält eine virtuelle Kamera, die direkt aus dem hochaufgelösten Foto schneidet, Figuren-Sprites mit Kontaktschatten, das Füllen freigelegter Grundplatte über das Noppengitter, eine Lupe als Übergang, Bauchbinden und den Stop-Motion-Look mit 12 Bildern pro Sekunde, Korn und minimalem Bildstand-Zittern. Vorlagen für Intro, Modellszene und Outro sind dabei. Die Regeln für Regie, Rhythmus, KI-Einsatz und Ton stehen in `skills/modelle-in-aktion/references/` und kommen aus der Produktion eines echten Werte-Films.

Schrift: Nunito (SIL Open Font License, liegt in `assets/fonts`). Eigene Schrift und Farben stellst du in `project.json` ein.

## Lizenz

MIT, © 2026 Ruben Langwara. Rückmeldungen und Verbesserungen gern als Issue oder Pull Request.
