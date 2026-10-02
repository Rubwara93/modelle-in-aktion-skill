# Fallen und Lösungen (aus der Praxis)

| Falle | Woran man sie erkennt | Lösung |
|---|---|---|
| Modell nicht wiedererkannt | Gruppe fragt »wo ist das Ganze?« | Jede Modellszene beginnt und endet in der Totale (Rein-/Rauszoom um denselben Fixpunkt). |
| Holzhände, Kärtchen, Nachbarplatten im Bild | KI macht daraus »Fingerbrei«, Kärtchen lenken ab | In Einzelszenen entfernen (Qwen, nur maskiert) oder Ausschnitt verschieben. Die Bauchbinde ersetzt das Kärtchen. In der Gesamtaufnahme dürfen sie bleiben, außer sie zeigen Namen oder Firmen. |
| KI-Kamerafahrt | Grundplatte wellt sich, Objekte fahren aus dem Bild | Nie die KI die Kamera bewegen lassen. Kamera immer selbst über `camera.World` aus dem Foto. |
| Organische Verformung | Rüssel wackelt, Tier läuft, Figur biegt sich | Starr bewegen (Sprite) oder statisch lassen. Plastik biegt sich nicht. |
| Eintönig | alle bewegen sich gleichzeitig ein bisschen | Eine Hauptaktion je Shot, andere warten. Halte nach jeder Aktion. Gemeinsame Beats bewusst setzen. |
| Zusatzobjekte gegen Clipende | zweiter Hund, Baum wird Palme, goldener Geist | Nur den sauberen Anfang des Clips nutzen. Rückwärts-Trick. Umgebung immer aus dem Foto. |
| Kling-Moderation »nsfw« | Aufruf abgelehnt (wird erstattet) | Prompt kürzen, neutrale Wörter (»toy figure«, »hops«), keine Haut-/Kleidungsfarben, kein »rope«. |
| Qwen ändert still Details | Gesichtsdruck anders, Farbe leicht verschoben | Nur Box/Maske um die gewollte Änderung zurückkopieren, vorher ausrichten. |
| Geist am alten Platz | Hand-/Fußreste bleiben stehen, wenn die Figur hüpft | Polygon 3–5 px großzügiger, Hände und Füße mitnehmen. |
| Noppen laufen unter der Figur schief | Platte unter der gehobenen Figur verschmiert oder versetzt | Gitter direkt neben der Figur messen (Perspektive!), nicht am anderen Plattenrand. |
| Farbfilter frisst die Figur | grünes Hemd verschwindet auf grüner Platte | `keep` nur bei klar abgesetzten Farben, sonst nur das Polygon. |
| Figur »schwebt« | kein Bodenkontakt beim Hüpfer | Kontaktschatten (`sprite.put`/`Hopper` machen ihn), Schatten bleibt am Boden. |
| Ausschnitt zu klein | Nahaufnahme weich | Ausschnitt ≥ ~1200 Fotopixel breit, sonst Totale näher fotografieren lassen oder halbnah bleiben. |
| Aktion unter der Bauchbinde | Figur oben links verdeckt | Ausschnitt so legen, dass die Hauptfigur rechts oder unten steht. |
| Text über Modellen | Titel/Schluss überdeckt Figuren | `TITLE_AT`/`BLOCK_AT` auf freie Tischfläche legen, im Kontaktbogen prüfen. Die Gesamtaufnahme sollte vorn Tisch zeigen. |
| Selbstgebaute Musik | klingt nach Spieluhr/Mittelalter | Immer Musikmodell mit Kompositionsplan, zwei Varianten zur Wahl. |
| Musik und Schnitt laufen auseinander | Schlusstreffer nicht auf Outro-Beginn | Abschnittsdauern exakt auf Segmentgrenzen. Bei Änderungen Takte verdoppeln statt neu erzeugen. |
| Lautheit zu hoch/Übersteuerung | Spitze über −1 dBTP nach AAC | `build_final.py` misst zweistufig und zielt auf −2,5 dBTP vor AAC. |
| Gruppe fühlt sich zurückgesetzt | ein Modell bekommt weniger Zeit/Aktion | Gleicher Rhythmus, ähnliche Länge, jede Szene hat einen Hero-Moment. |
| Namen im Film | Kärtchen oder Flipchart mit Vornamen im Bild | Vor jedem Upload und im fertigen Film prüfen. Schwärzen (`photo_tools.py redact`) oder Ausschnitt ändern. |
| Hochformatfoto | in 16:9 passen hohe Elemente (Baum, Kran, Fahne) und die ganze Platte nicht zusammen, Nachbarmodelle ragen seitlich ins Bild | Totale = ganze Platte in voller Breite, Hohes darf oben angeschnitten sein und bekommt seinen Auftritt in der Nahaufnahme; oder `World(pad_top=…)` für Kopffreiheit; Nachbarn per engerem Ausschnitt oder Qwen (maskiert) entfernen. Für künftige Workshops: Modelle quer und mit Abstand zu den Nachbarn fotografieren lassen. |
| Figur steht in einem Gefäß (Pokal, Boot, Turm) | beim Hüpfen wird »Platte« in den Pokal gefüllt oder ein heller Fleck | `Hopper(..., bg_fill=…)`: Loch mit der Farbe/dem Verlauf des Innenraums füllen (z. B. dunkle Ellipse aus dem Innenrand gemessen) und die Vorderkante des Gefäßes nach dem Hüpfer wieder über die Figur legen. |
| Gesamtaufnahme zeigt mehr Modelle als der Film | Steinreihe/Outro passt nicht zum Bild | Intro/Outro-Ausschnitt auf die gezeigten Modelle legen; wenn das nicht geht, alle zeigen und im Titel nichts zählen (»Unsere Werte« statt »Zwei Werte«). |
| Hüpfer hinterlässt Schliere trotz Gitter | Meldung »Noppenversatz 0 px« | Arbeitsrand zu klein für die Spender: `margin` größer (Standard ist aus Gitter und Hub abgeleitet), oder freies Plattenstück fehlt neben der Figur → `bg_fill`. |
| Lange Renderzeit | 2 min und mehr je Segment bei 24-MP-Fotos | Die Vorlage kopiert nur den sichtbaren Teil (`camera.shoot_array`). Für Proben `--only` nutzen, ganz rendern erst, wenn die Probebilder stimmen. |
