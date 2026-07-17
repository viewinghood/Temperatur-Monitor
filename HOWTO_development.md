# HOWTO — Entwicklung & Dateikatalog

**Stand:** 2026-07-17  
**Workspace (Lenovo):** `C:\Users\ritchie\temp_monitor`  
**Produktiv (Pi):** `/home/pi/py/TempMonitor/dev/`

Dieses Dokument ordnet die Dateien nach Nutzen. Produktivcode liegt flach im Repo-Root (einfaches Deploy auf den Pi). Entwicklungsmaterial liegt in `_archive/`, `docs/` und `legacy/`.

Terminal-Schnellhilfe Display: **[HOWTO_terminal_display.md](HOWTO_terminal_display.md)**

---

## 1. Repo-Struktur (Kurz)

```
temp_monitor/
├── README.md                     # Einstieg GitHub / Installation
├── HOWTO_development.md          # dieser Katalog
├── HOWTO_terminal_display.md     # SSH: Touch ↔ HDMI
├── requirements.txt
├── .gitignore
│
├── tm_pyqt_plot_app.py           # PRODUKTIV HDMI
├── tm_pyqt_touch_app.py          # PRODUKTIV Touch
├── tm_*.py / spi_adc_tm_try4.py  # gemeinsame Module
├── set_touch_display.sh          # Display-Umschaltung
├── launch_*.py / start_*.sh      # Start / Desktop
├── *.desktop / install_*.sh
│
├── legacy/kivy/                  # Kivy-Versuch (nicht Produktiv)
├── docs/reports/                 # Architektur, Bullseye-Setup
├── docs/screenshots/             # Erfolgs-/Debug-Bilder
├── _archive/backups/             # *.bak Kopien
├── _archive/experiments/         # Einmal-Skripte, alte Versuche
├── _archive/history/             # Chat-/Session-Dumps
├── pi_bullseye_backup/           # SD-/OS-Referenz Bullseye
├── pi_stretch_backup/            # alter Stretch-Stand
└── pi_images/                    # Flash-/Recovery-Hilfen Windows
```

---

## 2. Produktiv — PyQt HDMI & Touch

### Apps

| Datei | Rolle |
|-------|--------|
| `tm_pyqt_plot_app.py` | **HDMI TempMonitor** — Desktop-Fenster, PyQtGraph OpenGL |
| `tm_pyqt_touch_app.py` | **Touch TempMonitor** — 800×448 borderless, Seitenleiste |

### Gemeinsame Logik

| Datei | Rolle |
|-------|--------|
| `tm_hw_worker.py` | SPI-Abtastung im `QThread` |
| `spi_adc_tm_try4.py` | ADS1118-Acquisition (U1/U2) |
| `ads1118.py` | Low-Level ADS1118 |
| `tm_csv_logger.py` | CSV-Logging |
| `tm_channels.py` | Kanal-Konfiguration |
| `tm_settings.py` | Plot-Fenster / Missing-Value Keys |
| `tm_settings_dialog.py` | Einstellungsdialog (HDMI) + Display-Switch |
| `tm_status.py` | Status-Texte |
| `tm_platform.py` | OS-/Log-Pfad-Anzeige |
| `tm_app_icon.py` | Fenster-/Taskbar-Icon |
| `tm_display_mode.py` | Touch-Modus-Flag + HDMI/Touch-Erkennung |
| `tm_display_switch.py` | Umschalten + Reboot-Trigger |
| `tm_hdmi_switch.py` | Alias → `tm_display_switch` |
| `tm_switch_hdmi_app.py` / `tm_switch_touch_app.py` | Kleine Confirm-Apps für Desktop-Icons |

### Start & Desktop

| Datei | Rolle |
|-------|--------|
| `launch_tm_hdmi.py` / `launch_tm_touch.py` | Desktop-Entry-Punkte (Singleton) |
| `start_tm_gui.sh` | HDMI starten |
| `start_tm_pyqt_touch_gui.sh` | Touch starten |
| `start_tm_switch_hdmi.sh` / `start_tm_switch_touch.sh` | Switch-Apps |
| `TempMonitor.desktop` | Icon **HDMI TempMonitor** |
| `TempMonitor-Touch.desktop` | Icon **Touch TempMonitor** |
| `SwitchToHDMI.desktop` / `SwitchToTouch.desktop` | Display-Wechsel |
| `set_touch_display.sh` | `touch` / `hdmi` / `status` (+ Reboot) |
| `install_touch_desktop.sh` | Desktop + pcmanfm/libfm Ein-Klick |
| `install_display_switch_desktop.sh` | Switch-Icons |
| `install_lxpanel_launcher.sh` | Launchbar Touch |
| `install_bullseye_gui.sh` | apt: PyQt5, pyqtgraph, spidev, (Kivy optional) |
| `install_bullseye_desktop.sh` | LXDE/LightDM Desktop-Stack |

### Doku-Generator

| Datei | Rolle |
|-------|--------|
| `build_app_mechanik_png.py` | Erzeugt `docs/reports/REPORT-app-mechanik.png` |

---

## 3. Legacy — Kivy (Referenz, nicht Produktiv)

Pfad: **`legacy/kivy/`**

Die Kivy-Version war der erste Touch-Weg (Stretch/Bullseye). Unter Bullseye + X11 ist **PyQt5 die Produktivlösung**. Die Dateien bleiben als Lern-/Referenzmaterial:

| Datei | Rolle |
|-------|--------|
| `tm_kivy_app.py` | Haupt-App (ScreenManager) |
| `tm_kivy_screens.py` | Plot / Channels / Settings / Logging |
| `tm_kivy_hw.py` | HW-Anbindung |
| `tm_kivy_bridge.py` | Brücke Plot ↔ Kivy |
| `tm_kivy_plot_app.py` | frühere Plot-Variante |
| `pg_plot_kivy_widget.py` | PyQtGraph offscreen → Bitmap für Kivy |
| `start_tm_kivy_gui.sh` | Startskript |
| `TempMonitor-Kivy.desktop` | Desktop-Icon (Legacy) |
| `kivy-config-input.snippet` | Touch-Input für `~/.kivy/config.ini` |
| `fix_kivy_config_ini.sh` | Kivy-Config reparieren |

Berichte dazu: `docs/reports/REPORT-kivy-touch-display.md`, Screenshots unter `docs/screenshots/REPORT-tm_kivy-*.png`.

---

## 4. Dokumentation (`docs/`)

### `docs/reports/`

| Datei | Nutzen |
|-------|--------|
| `REPORT-app-design.md` | Architektur HDMI + Touch + Threads + OpenGL |
| `REPORT-app-mechanik.png` | Ein-Seiten-Schaubild |
| `REPORT-ads1118-pi3.md` | SPI / ADS1118 Hardware |
| `REPORT-kivy-touch-display.md` | Kivy + DSI Display-Setup |
| `BULLSEYE_WORKING_SETUP.md` | Image, config.txt, SSH, Apt, GUI-Stack |

### `docs/screenshots/`

Erfolgs- und Debug-Screenshots (Desktop, Panel, TempMonitor, Kivy).

---

## 5. Archiv (`_archive/`)

| Ordner | Inhalt |
|--------|--------|
| `_archive/backups/` | Alle `*.bak` / `*.bakN` — lokale Sicherungskopien (kein GitHub-Zwang) |
| `_archive/experiments/` | Einmalige Fixes: Python 3.11-Build, pip-Versuche, `try2`/`try3` SPI, Night-Monitor, Recovery, Probe-Skripte |
| `_archive/history/` | Lange Cursor-/Chat-Exports, Agent-Fragen, alte Setup-Notizen |

**Regel:** Produktivcode ändern → vorher `.bak` lokal legen (bleibt in `_archive/backups/` oder neben der Datei). Kleines Projekt → Backups zählen mehr als „nur Git“.

---

## 6. Pi-Backups & Images (nicht App-Code)

| Ordner | Nutzen |
|--------|--------|
| `pi_bullseye_backup/` | `/boot/config.txt`, apt, lightdm, Paketlisten — **Referenz für Neuinstallation** |
| `pi_stretch_backup/` | Alter Stretch-Stand (nur lokal, nicht im öffentlichen Repo) |
| `pi_images/` | Windows PowerShell: Safe-Boot, HDMI-Fix, Flash-Nacharbeit |

**Achtung:** SSH-Keys unter `pi_bullseye_backup/home/pi/.ssh/` gehören **nicht** ins öffentliche GitHub (siehe `.gitignore`).

---

## 7. Deploy Lenovo → Pi

Typisch (aus dem Repo-Root):

```bash
scp tm_pyqt_*.py tm_*.py spi_adc_tm_try4.py ads1118.py set_touch_display.sh \
    launch_*.py start_*.sh *.desktop install_*.sh \
    pi@<PI_IP>:~/py/TempMonitor/dev/
```

Oder gezielt einzelne geänderte Module. Nach Desktop-Install:

```bash
ssh pi@<PI_IP> "bash ~/py/TempMonitor/dev/install_touch_desktop.sh"
```

Display-Wechsel: [HOWTO_terminal_display.md](HOWTO_terminal_display.md).

---

## 8. GitHub-Vorbereitung (Checkliste)

- [x] Root aufgeräumt (Produktiv klar getrennt)
- [x] Backups / Experimente / History archiviert
- [x] Kivy unter `legacy/kivy/`
- [x] `README.md` mit Voraussetzungen
- [x] `.gitignore` (Cache, Logs, Secrets, große Images)
- [x] `requirements.txt` (PC / Hinweis Pi-apt)
- [ ] Remote anlegen (`gh repo create` oder GitHub-Web)
- [ ] Erster Commit / Push (bewusst, wenn du es willst)

Lokal initialisieren (ohne Push):

```powershell
cd C:\Users\ritchie\temp_monitor
git init
git add .
git status
```

---

## 9. Was wohin gehört — Entscheidungshilfe

| Frage | Antwort |
|-------|---------|
| Läuft auf dem Pi im Alltag? | Root: `tm_pyqt_*`, Worker, SPI, Desktop, `set_touch_display.sh` |
| Nur Lern-/Altstand Kivy? | `legacy/kivy/` |
| Architektur verstehen? | `docs/reports/REPORT-app-design.md` |
| OS neu flashen? | `docs/reports/BULLSEYE_WORKING_SETUP.md` + `pi_bullseye_backup/` |
| Alte `.bak`? | `_archive/backups/` |
| Einmal-Skript von der Session? | `_archive/experiments/` |
