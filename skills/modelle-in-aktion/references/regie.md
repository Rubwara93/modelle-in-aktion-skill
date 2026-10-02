# Regie: vom Modellfoto zur Szene

Der Film lebt davon, dass die Teilnehmenden **ihr** Modell wiedererkennen und jede Bewegung zu dem passt, was sie gebaut und erzählt haben. Ein hübsch animiertes Modell mit der falschen Bedeutung wirkt auf die Gruppe beliebig. Deshalb kommt die Analyse vor jeder Animation, und sie stützt sich auf Belege.

## Inhalt
1. Quellen und was mit ihnen passieren darf
2. Interview mit der Person, die den Film bestellt
3. Analyse je Modell (Spezifikation)
4. Zwei Kritiken
5. Schnittplan und Bildplan

## 1. Quellen

| Quelle | Wofür | Darf an KI-Dienste? |
|---|---|---|
| Foto je Modell (Originalauflösung) | alles: Ausschnitte, Sprites, Startbilder | nur als Ausschnitt **ohne Personen, Gesichter, Namen** |
| Gesamtaufnahme aller Modelle | Intro, Outro | in der Regel nein (Raum, Personen am Rand) |
| Flipcharts, Mitschriften, Transkripte (`private/`) | Bedeutung, Metaphern, Zitate der Gruppe | **nie**, nur lokal lesen. Vornamen und Zitate kommen nie ins Video |
| Werte-/Ergebnistexte (Name, Claim) | Bauchbinden | – |

In Fotos immer hineinzoomen (`photo_tools.py grid … --box`), bevor du etwas behauptest. Auf 24-MP-Fotos sind Details zu sehen, die in der Übersicht fehlen (Münzen, Drucke auf Köpfen, Schnüre, Kleinteile).

## 2. Interview

Frag in einer Runde, mit Empfehlung je Frage, nur was nicht im Material steht:

- Wofür ist der Film? (Präsentation vor der Gruppe mit Ton, Endlosschleife ohne Ton, Social Media) → Länge, Lautheit, Texte.
- Darf die Organisation erkennbar sein? Wenn nicht: kein Firmenname, kein Logo, keine Kärtchen mit Firmennamen im Bild.
- Je Modell: Name/Wert, Claim (offizieller Wortlaut), kurze Kategorie-Marke (optional, z. B. »Wert 1«), Farbe.
- Je Modell: Was hat die Gruppe erzählt? Welche Teile tragen die Bedeutung (»das Boot heißt: alle in einem Boot«)?
- Titel und Schlusszeilen. Absender (»Leadership Team«), wenn gewünscht.
- Musikrichtung (eher warm/handgemacht, eher elektronisch …) und was auf keinen Fall.
- Budget für KI-Aufrufe (typisch 5–15 $ für 5 Modelle).

## 3. Analyse je Modell → `plan/specs/<key>.json`

Für jedes sichtbare Element:

```json
{
  "element": "Blaues Schlauchboot, Bug zeigt zur Kamera",
  "where": "links neben der Grundplatte",
  "bbox": [215, 343, 660, 799],
  "metaphor": "Alle sitzen in einem Boot: gemeinsame Verantwortung.",
  "evidence": "Flipchart: »wir sind gemeinschaftlich verantwortlich«; Hinweis der Auftraggeberin",
  "confidence": "hoch | mittel | Vermutung",
  "motion_potential": "bleibt fest stehen – steht auf dem Tisch, nicht auf Wasser; Ort, an dem die Handlung ankommt"
}
```

Dann für das Modell:
- `story`: drei bis fünf Sätze, was in der Szene passiert, in der Logik der Metapher.
- `core_message`: ein Satz, was die Gruppe beim Zuschauen wiedererkennen soll.
- `shots`: Totale, Nah, Rückweg; je Shot Rolle, Ausschnitt (bbox im Originalfoto), Bewegungen, Technik (Sprite, Hüpfer, KI-Clip, Pose-zu-Pose), Hero-Moment.
- `sfx`: je sichtbarem Ereignis ein Geräusch (Zeit, Beschreibung, englischer Prompt).
- `open_questions`: was unsicher ist, was bewusst weggelassen wurde und warum.

Bewegungsregeln, die aus der Praxis kommen:
- **Plastik ist starr.** Figuren bewegen sich in Posen: Hüpfer, Drehung, Ruck, Arm an der Schulter. Nichts biegt sich, kein Rüssel wackelt, kein Tier läuft organisch.
- **Wenige Bewegungen, nacheinander.** Eine Hauptaktion pro Shot, die anderen Elemente warten. Viele gleichzeitige Kleinbewegungen im selben Tempo wirken eintönig.
- **Was physisch verbunden ist, bleibt stehen** (Leiter am Elefanten, Netz über der Herde, Schnüre an Figuren), es sei denn, du kannst alles zusammen bewegen.
- **Ruhige Gegenpole** sind erlaubt und nötig: Die Herde bleibt stehen, damit die Mannschaft auffällt.
- **Bedeutung schlägt Effekt.** Eine Kamerafahrt, die etwas aus dem Bild schiebt oder die Grundplatte verbiegt, zerstört das Modell.

## 4. Zwei Kritiken

Lass die Spezifikation von zwei Seiten prüfen (zwei Subagenten oder zwei getrennte Durchgänge):

- **Handwerk (Stop-Motion):** Ist jede Bewegung mit Sprites/Masken aus diesem Foto machbar? Was wird freigelegt, und gibt es dafür Material (Platte, Tisch)? Liegt die Aktion außerhalb der Bauchbinden-Zone oben links? Sind Hero und Beats auf dem Raster?
- **Bedeutung:** Erzählt die Bewegung, was die Gruppe gemeint hat? Ist eine Deutung Vermutung, und ist sie dann zurückhaltend inszeniert? Würde die Gruppe sich missverstanden fühlen?

Übernimm, was trägt, und schreibe in `open_questions`, was du verworfen hast und warum.

## 5. Schnittplan und Bildplan

`plan/edit_plan.json`: Reihenfolge, Dauer je Segment, Hero-Schlag absolut, Übergänge, Einblendungen. Danach je Segment einen **Bildplan** in den Kopf des Segment-Skripts (Vorlage in `assets/templates/segment_modell.py`): Bildnummer → Aktion → Geräusch mit Zeit. Erst wenn der Bildplan steht, Code schreiben. Der Bildplan ist zugleich die Liste für die Geräusch-Cues.

Zeig der Person nach der Analyse die Geschichten je Modell (kurz, im Chat) und hol ein Okay, bevor Geld für KI-Aufrufe ausgegeben wird.
