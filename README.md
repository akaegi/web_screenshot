# Web Screenshot

Erzeugt einen Screenshot von einem oder mehreren Elementen einer Webseite und stapelt sie
vertikal in ein PNG. Gedacht zum Beispiel für eine Wetterprognose als Bild im
Home-Assistant-Dashboard (Shelly Wall Display X1i, 720×720).

## Inhalt

| Pfad | Zweck |
|---|---|
| `addon/screenshot.py` | Das Script (Playwright + Pillow), auch direkt auf dem Mac nutzbar |
| `addon/` | Lokales Home-Assistant-Add-on, das `screenshot.py` einmal ausführt |
| `docs/konversation.md` | Zusammenfassung der Entstehung, Entscheidungen und verworfenen Varianten |

## addon/screenshot.py

Abhängigkeiten stehen als Inline-Metadaten im Script, es läuft direkt mit `pipx run` oder `uv run`.

```bash
pipx run addon/screenshot.py \
  "https://weather.com/" \
  '[data-testid="current-conditions"]' \
  --output weather.png \
  --hide '[id^="sp_message_container"]'
```

| Option | Bedeutung |
|---|---|
| `URL SELECTOR [SELECTOR ...]` | Seite und ein oder mehrere Elemente, von oben nach unten gestapelt |
| `--output` | Ziel-PNG (wird über eine temporäre Datei geschrieben und dann umbenannt) |
| `--hide SELECTOR` | Element mit `display: none` ausblenden, mehrfach möglich |
| `--style SELECTOR CSS` | Inline-Styles setzen, z. B. `"overflow: hidden"`, mehrfach möglich |
| `--width`, `--height` | Viewport, Standard 720×720 |
| `--gap`, `--margin` | Abstand zwischen den Elementen bzw. Rand, Standard je 10 px |
| `--timezone`, `--locale` | Standard `Europe/Zurich`, `de-CH` |
| `--cdp URL` | Entfernter Browser (Browserless `wss://…?token=…`, lokales Chrome `http://127.0.0.1:9222`); ohne startet lokal Chromium |

Selektoren werden über Playwright-Locators aufgelöst und durchdringen offenes Shadow DOM.
Mit `host >> selector` lässt sich innerhalb eines Elements weitersuchen.

Lokales Chrome als CDP-Server (macOS):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-cdp"
```

## Home-Assistant-Add-on

Das Add-on enthält keinen Browser (Image ca. 200 MB statt 1 GB), gerendert wird über Browserless.
Es läuft einmal durch und beendet sich; wann es läuft, bestimmt eine HA-Automation.

Für Browserless auf [browserless.io](https://www.browserless.io) ein Konto anlegen, im Dashboard den
API-Token kopieren und in `cdp_url` die URL samt Token eintragen, zum Beispiel
`wss://production-sfo.browserless.io?token=…` (gültige Regionen stehen im Dashboard). Das Token
gehört nicht ins Repository.

Statt des gehosteten Browserless geht auch ein CDP-Server im lokalen Netzwerk, zum Beispiel ein
eigener Browserless-Container oder ein Chrome auf einem anderen Rechner. Dafür in `cdp_url`
dessen Adresse eintragen, etwa `ws://192.168.1.10:3000?token=…` oder `http://192.168.1.10:9222`.
Die IP-Adresse verwenden, und der Server muss vom Add-on aus erreichbar sein (Chrome lauscht
standardmässig nur auf `127.0.0.1`). Ein CDP-Port ohne Token gibt jedem im Netz die volle Kontrolle
über den Browser, also nur in einem vertrauenswürdigen Netz offen lassen.

### Installation

Das Add-on lässt sich von GitHub beziehen oder lokal hineinkopieren. In beiden Fällen baut Home
Assistant das Image aus dem `Dockerfile` auf dem eigenen Gerät.

**Variante A: von GitHub**

1. Einstellungen → Add-ons → Add-on-Store → ⋮ → «Repositories» →
   `https://github.com/akaegi/web_screenshot` hinzufügen.
2. «Web Screenshot» im Store installieren.

**Variante B: lokal**

1. Über das Add-on «Samba share» oder «Advanced SSH & Web Terminal» den Ordner
   `/addons/web_screenshot/` anlegen und den Inhalt von `addon/` hineinkopieren
   (`config.yaml`, `Dockerfile`, `run.py`, `screenshot.py`).
2. Einstellungen → Add-ons → Add-on-Store → ⋮ → «Nach Updates suchen» → «Web Screenshot» installieren.

**Danach in beiden Fällen:** Im Tab Konfiguration `cdp_url`, `url` und `selectors` eintragen
(Beispiel unten), speichern, einmal von Hand starten und das Protokoll prüfen.

Beispielwerte für die aktuellen Bedingungen von weather.com (die weiteren Abschnitte gehen von
`weather.png` aus):

```yaml
url: https://weather.com/
selectors:
  - '[data-testid="current-conditions"]'
hide:
  - '[id^="sp_message_container"]'
output: weather.png
```

`hide` blendet das Cookie-Banner aus. weather.com wählt den Ort anhand der IP-Adresse des Browsers,
mit Browserless also den Standort des Browserless-Servers; für einen festen Ort die URL der
entsprechenden Ortsseite verwenden.

Nach Änderungen an `config.yaml` die Version erhöhen und erneut «Nach Updates suchen»;
nach Änderungen an den übrigen Dateien im Add-on ⋮ → «Neu erstellen». Bei Variante A vorher pushen
und ebenfalls «Nach Updates suchen», damit Home Assistant den neuen Stand von GitHub holt. Ein
Update wird im Store nur angezeigt, wenn die Version erhöht wurde.

Das Bild landet in `/media/screenshots/weather.png` (siehe `map: media:rw` in `config.yaml` und
`OUTPUT_DIR` in `run.py`). Das Add-on sieht nur den Media-Ordner und hat keinen Zugriff auf die
HA-Konfiguration.

### Kamera, Automation, Karte

Kamera: Integration **Local File** mit Pfad `/media/screenshots/weather.png`, oder per YAML:

```yaml
camera:
  - platform: local_file
    name: Wetter
    file_path: /media/screenshots/weather.png
```

Automation (stündlich um :10, nachts Pause, schont die Browserless-Einheiten):

```yaml
alias: Web-Screenshot aktualisieren
triggers:
  - trigger: time_pattern
    minutes: 10
conditions:
  - condition: time
    after: "05:00:00"
    before: "22:00:00"
actions:
  - action: hassio.addon_start
    data:
      addon: local_web_screenshot
```

`local_web_screenshot` gilt für Variante B. Bei Variante A beginnt die ID stattdessen mit einem Hash
des Repositorys (`<hash>_web_screenshot`); sie steht in der URL der Add-on-Seite.

Karte:

```yaml
type: picture-entity
entity: camera.wetter
camera_view: auto
show_name: false
show_state: false
```
