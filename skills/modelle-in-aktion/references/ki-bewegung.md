# KI-Bewegung und KI-Bildbearbeitung (fal.ai)

Grundsatz: **Das Foto bleibt die Grundebene. KI darf bewegen, nicht umgestalten.** Ein KI-Clip ersetzt nie das ganze Bild, sondern liefert nur die Pixel der Figur, die sich bewegt. Alles andere kommt aus dem scharfen Foto.

## Wann was

| Bewegung | Werkzeug |
|---|---|
| starrer Hüpfer, Ruck, Drehung um die Hochachse, Rutschen | Sprite aus dem Foto (`sprite.Hopper`, `sprite.put`) – kostenlos, am echtesten |
| Arm hebt sich, Kopf dreht sich, Figur setzt sich, steigt ein | Kling-Clip (maskiert) oder Pose-zu-Pose mit Qwen-Zielbild |
| Licht an/aus (Ampel, Lampe), Glühen | PIL (`core.glow`, eigene Maske) |
| Münzen, Funken, Konfetti | PIL-Sprites aus dem Foto, gestaffelt |
| Objekt entfernen (Holzhand, Kärtchen, Nachbarplatte) | Qwen-Edit, nur in der Maske übernehmen |

## Kling 3.0 Pro (Image-to-Video)

`python3 <skill>/scripts/fal_api.py kling work/<key>/nah-start.jpg plan/prompts/<shot>.txt clips/<shot>-t1.mp4 [--end zielbild.jpg] [--duration 5] [--cfg 0.6]`

- **Startbild** = 16:9-Ausschnitt aus dem Originalfoto (`photo_tools.py crop`), ohne Personen, Hände, Kärtchen und Namen. Kling übernimmt das Seitenverhältnis vom Startbild.
- **Endbild** (optional) gibt die Zielpose vor. Kling interpoliert dazwischen. Ein Endbild baust du mit Qwen (»Change only … the figure now stands inside the boat …«) und kopierst nur die Figurbox zurück ins Foto.
- **Rückwärts-Trick:** Kling bewegt Figuren am liebsten *aus* der gebauten Pose heraus. Dann den Clip rückwärts abspielen (`keys` in `core.remap` fallend): Die Figur kommt in ihre gebaute Pose und endet pixelgenau auf dem Foto.
- **Prompts kurz und neutral**, Englisch, ohne Kamera: »The small toy figure on the left raises its right arm and points to the boat. Everything else stays still. Static camera.« Die Moderation lehnt manche harmlosen Wörter ab (Rückmeldung »nsfw«, wird erstattet). Ausgelöst haben u. a. Tiernamen mit Farbadjektiv, »rope«, »arm straight up«, lange Figurenbeschreibungen mit Haut- oder Kleidungsfarben. Ersetzen durch »toy figures«, »hops«, »leans back as if rowing«.
- `cfg` 0,5–0,7. `generate_audio` ist aus (spart ein Drittel, Ton kommt aus der eigenen Mischung).
- **Jedes Bild prüfen** (Kontaktbogen des Clips): Verzerrte Zwischenbilder (Lupe verdreht, Krone doppelt, Figur verschmiert) überspringen und lieber ein Bild länger halten. Gegen Clipende tauchen oft Zusatzobjekte auf. Diesen Teil nicht verwenden.
- **Einbau:** `C.align` gegen Kameradrift (statische Box ohne Bewegung angeben), `C.color_match` im Ring um die Maske, `C.paste` mit weicher Maske (Ellipse/Polygon um die Figur plus Bewegungsraum, oder `C.diff_mask`). Danach im 12-fps-Takt neu timen (`remap`), oft mit Tempo 1,5×.
- Kosten: ~0,11 $ je Sekunde. Ein 5-s-Clip ~0,56 $. Pro Modell meist 1–2 Clips, Wiederholungen eingerechnet ~1–2 $.

## Qwen Image Edit

`python3 <skill>/scripts/fal_api.py qwen <bild> <anweisung.txt> <out.png> [--size 1920x1080]`

- Anweisung: »Change only …«, dann nummeriert, was sich ändert, und ausdrücklich, was bleibt.
- **Nie das ganze Ergebnis übernehmen.** Qwen verändert still Details (Gesichtsdrucke, Farben, Kleinteile). Nur in einer Box oder Maske um die gewollte Änderung zurückkopieren (`sprite.blend_mask_region`), sonst ist das Modell nicht mehr das der Gruppe.
- Qwen-Bilder sind gegen das Original oft um einige Pixel verschoben → vorher ausrichten (`C.align` auf einen statischen Bereich).
- Manche Anweisungen schlagen reproduzierbar fehl (z. B. »Boden ersetzen«). Dann ohne KI lösen: `fill.shift_fill`, `fill.inpaint`.
- Kosten ~0,03 $ pro Megapixel, also ~0,06 $ pro Bild.

## Freigelegte Flächen

Wenn eine Figur hüpft, sich dreht oder umsteigt, wird darunter Platte sichtbar.
1. **Noppengitter direkt neben der Figur messen** (`fill.estimate_lattice` auf einem freien Plattenstück von mind. ~6×4 Noppen in der Nähe). Die Perspektive ändert den Gittervektor über die Platte. Ein Wert vom anderen Plattenrand liegt nach zwei Reihen schon eine halbe Noppe daneben.
2. `fill.shift_fill` füllt aus der um ganze Noppen versetzten Platte, `fill.inpaint` für Tisch und Reste.
3. **Polygon eng, aber vollständig:** 3–5 px außerhalb der Figur nachzeichnen, Hände und Füße mit. Reste der Originalfigur bleiben sonst als Geist stehen. Zu weite Polygone heben Plattenstücke mit an. Farbfilter (`keep`) nur, wenn die Figur keine Farbe mit dem Untergrund teilt (grünes Hemd auf grüner Platte geht nicht).

## Datenschutz bei Uploads

Hochgeladen werden nur Modellausschnitte. Keine Flipcharts, keine Gesichter, keine Namen, keine Raumaufnahmen mit Personen. Falls ein Ausschnitt Namen auf Kärtchen zeigt: vorher `photo_tools.py redact`. Jede Person nutzt ihren eigenen fal.ai-Schlüssel, und die Dateien liegen dort im Speicher des eigenen Kontos.
