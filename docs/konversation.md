# Entstehung: Wetterbild für das Shelly Wall Display

Zusammenfassung einer Konversation mit Claude (29. September bis 5. November 2026).
Kein wörtliches Protokoll, sondern die Fragen, Entscheidungen und Erkenntnisse in Reihenfolge.

## 1. Display

- **Shelly Wall Display X1i:** 4", 720×720 px, 86,5×86,5 mm, Android 11, RK3326-S, 1 GB RAM,
  5-A-Relais in austauschbarer Power Base, nur WLAN. Kein Temperatur-/Feuchtesensor
  (nur Licht-, Näherungs- und Gestensensor).
- HA-Dashboard ist eingebaut: Settings → Network → Home Assistant, Dashboard-URL eintragen.
  Die untere Shelly-Leiste lässt sich seit FW 2.3.0 auf der HA-Seite ausblenden.
- Swipe zwischen HA-Views via HACS «Swipe Navigation» möglich, kann aber mit Shellys eigener
  Wischgeste kollidieren. Alternative: Navigations-Buttons im Dashboard, kiosk-mode für Vollbild.
- Verglichene Alternativen: Sonoff NSPanel Pro 86 (3,95", 480×480, Zigbee, kein Relais, träge),
  NSPanel Pro 120 (4,7", 750×1334, 120-mm-Dose), generische Android-PoE-Panels.

## 2. Wetterdaten

- Wetterdienste bieten oft keine fertigen Bilder per API. Offene Daten enthalten Werte und
  Wettersymbol-Nummern, die sich mit eigenen Icons kombinieren lassen; die Grafiken der Anbieter
  sind nicht unbedingt zur Weiterverwendung freigegeben.
- Alternative: freie Wetter-API (JSON, WMO-Codes, ohne API-Key).
- Entscheid vorerst: Screenshot einer Prognose-Seite.

## 3. Script

Schrittweise entstanden:

1. `shot-scraper` scheiterte am Shadow DOM (`-s` nutzt `document.querySelector`).
   Workaround mit Marker-`div` per `-j` möglich, verworfen zugunsten von Playwright.
2. Playwright-Locators durchdringen offenes Shadow DOM; Chaining mit `host >> selector`.
3. Ausführung mit `pipx run` / `uv run` dank Inline-Metadaten (`# /// script`).
4. Erweitert um mehrere Selektoren (vertikal gestapelt, zentriert, Hintergrund = Pixel oben links),
   `--gap`, `--margin`, `--hide`, `--style`, `--width/--height`, `--timezone/--locale`, `--cdp`.
5. Ausgabe über temporäre Datei + `os.replace`, damit HA nie ein halbes Bild sieht.

## 4. Wo läuft der Browser?

| Variante | Ergebnis |
|---|---|
| HA-Add-on mit Chromium | Funktioniert, Image ~1 GB — zu gross fürs Embedded-System |
| GitHub Actions + Pages | Gratis bei öffentlichem Repo, aber Pages ist immer öffentlich (auch bei privatem Repo). Später: Auslösen per `workflow_dispatch` aus HA (`rest_command`) |
| GitHub Actions + S3 | Gratis bei öffentlichem Repo, Bild unter zufälligem Namen; nicht umgesetzt |
| Google Cloud Run (Job oder Service) | Region Zürich, auch alle 15 Min. im Gratis-Kontingent; nicht umgesetzt |
| Heroku / Render / Railway / Fly.io | 512 MB oft zu knapp für Chromium; Heroku mit 1 GB erst 50 USD/Monat |
| SnapDeploy | Ungeeignet: Gratis-Container wachen nur per Browser-Aufruf auf, keine Jobs, Container müssen als Webserver laufen |
| **Browserless (gehostet)** | **Gewählt.** Gratis 1000 Einheiten/Monat (à 30 s), stündlich 6–22 Uhr ≈ 490 Einheiten. Alle 15 Min. bräuchte den Plan für 25 USD/Monat |
| Eigener VPS mit Browserless-Container | Option: Hetzner CX23 ~6 €/Monat, Zugriff nur über Tailscale |
| Moli (Rust-Headless-Browser) | Getestet, verworfen: kein `networkidle`, 256-MB-Rastergrenze, falscher Element-Ausschnitt, Diagramm-SVG nicht fertig gezeichnet |

## 5. Home-Assistant-Add-on (aktueller Stand)

- Ohne Browser im Image (nur Playwright-Client + Pillow, ~200 MB).
- `startup: once`, `boot: manual`: HA startet das Add-on per Automation
  (`hassio.addon_start`, `local_web_screenshot`), dadurch Nachtpause und weitere Bedingungen in HA.
- `run.py` übersetzt nur noch `/data/options.json` in Argumente für `screenshot.py`.
- Anzeige über Local-File-Kamera + `picture-entity`-Karte (vermeidet Browser-Cache von `/local/`).
- Das Add-on sieht nur den Media-Ordner (`media:rw`) und schreibt nach `/media/screenshots`.

## 6. Langfristige Idee

Diagramm ohne Browser selbst zeichnen (Open Data + matplotlib/Pillow): kaum RAM, exakt auf 720×720
ausgelegt und ohne Fragen zum Urheberrecht fremder Grafiken.
