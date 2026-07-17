# TempMonitor — Touch-Display & Kivy GUI (try4)

Report date: 2026-07-05  
Pi: Raspberry Pi 3 Model B, Raspbian Stretch (32-bit), `/home/pi/py/TempMonitor/dev/`

---

## 1. Bildschirmumstellung: HDMI → 7" DSI Touch

### Ausgangslage

| Setting | Wert | Wirkung |
|---------|------|---------|
| `ignore_lcd=1` | aktiv (seit 2019) | Offizielles 7"-DSI-Panel **absichtlich deaktiviert** (Eizo per HDMI) |
| `lcd_rotate=2` | aktiv | LCD um 180° gedreht |
| `start_x=0` | aktiv | Kein Desktop/X11 — Kivy läuft direkt auf Framebuffer (DISPMANX) |
| HDMI | 1280×1024 Eizo | War primäre Anzeige (`tvservice -s`) |

### Geplante Änderung (Touch — noch nicht aktiv)

**Datei auf dem Pi:** `/boot/config.txt`  
**Backup (Original HDMI):** `/boot/config.txt.bak-pre-touch`

**Status 2026-07-05:** Änderung wurde kurz getestet, dann **zurückgesetzt** — Pi läuft weiter mit **HDMI (Eizo)**. Touch-Umstellung erst nach Python/Kivy-Setup.

```ini
# Aktuell (HDMI, Standard):
ignore_lcd=1 # 7"LCD is off then
lcd_rotate=2

# Für Touch später:
#ignore_lcd=1  # auskommentieren
display_default_lcd=1
lcd_rotate=2   # unverändert
```

### Zurück zu HDMI (Revert)

Falls nach Touch-Test wieder der **HDMI-Monitor** genutzt werden soll:

```bash
# Option A — Backup wiederherstellen (empfohlen):
sudo cp /boot/config.txt.bak-pre-touch /boot/config.txt
sudo reboot

# Option B — manuell in /boot/config.txt:
#   Zeile wieder aktivieren:  ignore_lcd=1 # 7"LCD is off then
#   Zeile entfernen:         display_default_lcd=1
sudo reboot
```

Nach Reboot prüfen:

```bash
tvservice -s    # erwartet: HDMI-DMT, z. B. 1280x1024
grep ignore_lcd /boot/config.txt   # muss ignore_lcd=1 zeigen
```

### Was bewusst nicht geändert wurde

- `hdmi_*` — HDMI nicht hart deaktiviert; bei abgestecktem HDMI-Kabel reicht `display_default_lcd=1`.
- `dtoverlay=vc4-kms-v3d` — bleibt auskommentiert (Legacy-Framebuffer, passend zu Stretch + Kivy `egl_rpi`).
- `start_x=0` — bleibt; Kivy startet ohne Desktop-Session.

### Nach Reboot prüfen

```bash
# Auf dem Pi (lokal am Touchscreen, nicht nur per SSH):
tvservice -s          # sollte DSI/LCD zeigen, nicht nur HDMI-DMT
ls -l /dev/input/event*
# Touch: meist event0 (DSI) — bei Bedarf evtest

# Kivy auf LCD erzwingen (falls HDMI noch hängt):
export KIVY_BCM_DISPMANX_ID=0
python3 tm_kivy_plot_app.py
```

**Reboot erforderlich:** `sudo reboot`

### Kivy Touch-Eingabe

Snippet: `kivy-config-input.snippet` → in `~/.kivy/config.ini` unter `[input]` einfügen (mtdev für offizielles Panel).

---

## 2. Neue Dateien (try4)

| Datei | Rolle |
|-------|-------|
| `spi_adc_tm_try4.py` | 1-Hz-Aquisition, nur aktiver Kanal / Chip-Temps |
| `pg_plot_kivy_widget.py` | PyQtGraph ↔ Kivy Texture-Bridge |
| `tm_kivy_plot_app.py` | Touch-UI (Hauptprogramm) |
| `ads1118.py` | Erweiterung: `transfer_delay_s`, `settle_s` für schnelle Reads |

Backups: `*.bak`, `ads1118.py.bak2`

---

## 3. Messzeiten (1 Wert pro Sekunde)

### try3 vs try4

| | try3 | try4 |
|---|------|------|
| Samples/Kanal | 8 | **1** |
| Settle | 120 ms | **50 ms** |
| Zyklus | alle 4 Kanäle nacheinander | **nur angezeigte Quelle** |
| Intervall | konfigurierbar | **1,0 s** fest (`SAMPLE_INTERVAL_S`) |

### Ablauf pro Sekunde

**Modus „TC Kanal“:** ein differentialer Read des gewählten TC (TC1–TC4); CJC aus Cache (Refresh alle 30 s).  
**Modus „Chip-Temp“:** U1- und U2-Junction-Temperatur, zwei Kurven (`U1 CJC`, `U2 CJC`).

Headless-Test:

```bash
python3 spi_adc_tm_try4.py --seconds 10 --mode tc --sensor 1
python3 spi_adc_tm_try4.py --seconds 10 --mode chip
```

---

## 4. Architektur Kivy-App

### Warum Kivy + PyQtGraph (Hybrid)?

- **Kivy:** Touch-optimiert, große Buttons, DISPMANX auf Pi 3/Stretch.
- **PyQtGraph:** Lange Zeitreihen, Zoom/Pan, mehrere Kurven — **kein natives Kivy-Widget**.

PyQtGraph basiert auf Qt (`QWidget`). Ein Qt-Widget lässt sich **nicht** in den Kivy-Widget-Baum einhängen.

### Gewählte Lösung: Off-Screen-Render-Bridge

```
┌─────────────────────────────────────────────────────────┐
│  Kivy Main Thread (Touch, Layout, Clock)                │
│  ┌───────────────────────────────────────────────────┐  │
│  │ PyQtGraphPlotWidget (Kivy Widget + Texture)       │  │
│  │   touch → pan / double-tap → auto-range           │  │
│  └───────────────────────┬───────────────────────────┘  │
│                          │ Queue: set_data, render      │
│  ┌───────────────────────▼───────────────────────────┐  │
│  │ Worker Thread: QApplication + hidden PlotWidget   │  │
│  │   grab() → RGBA → Kivy Texture                    │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         ▲
         │ Lock + latest sample
┌────────┴────────┐
│ Acquisition     │  threading.Thread, 1 Hz
│ TempMonitorAcq  │  spi_adc_tm_try4.py
└─────────────────┘
```

### Parallelisierung (Design-Entscheidung)

| Mechanismus | Verwendung |
|-------------|------------|
| **`threading.Thread`** | ADC-Messung (`_acquisition_loop`) — blockiert SPI, darf UI nicht blockieren |
| **`threading.Lock`** | Übergabe des letzten Samples an UI |
| **`Clock.schedule_interval`** | Kivy-Hauptthread pollt Queue alle 0,2 s → Widget-Updates nur im Main Thread |
| **Kein `asyncio`** | Kivy 1.x nutzt eigenen Event-Loop; Mischung mit asyncio wäre auf Stretch unnötig komplex |
| **Kein `multiprocessing.Pipe`** | 1 Hz, kleine Dicts — Lock reicht; Pipe wäre Overhead |

Kivy-Regel: **Widgets nur im Main Thread anfassen** — daher `Clock`, nicht direktes Update aus dem Mess-Thread.

### UI-Layout (Touch-Guidelines)

```
┌──────────────────────────────────────┐
│ Statuszeile (aktueller Wert, 22sp)   │
├──────────────────────────────────────┤
│                                      │
│         PyQtGraph Plot               │
│         (flex, pan/zoom)             │
│                                      │
├──────────────────────────────────────┤
│ Hinweis: Wischen / Doppeltippen      │
├──────────────────────────────────────┤
│ [ TC Kanal ] [ Chip-Temp (CJC) ]     │  ≥ 56 dp Höhe
├──────────────────────────────────────┤
│ [TC1] [TC2] [TC3] [TC4]              │
└──────────────────────────────────────┘
```

- Touch-Ziele ≥ **48 dp** (Material: 48 dp minimum) → hier **56 dp**
- Kontrast: dunkler Hintergrund `#1a1a2e`, helle Achsen
- ToggleButton-Gruppen: exklusive Auswahl Quelle / Kanal
- Beim Kanal- oder Moduswechsel: Plot-Historie zurücksetzen

### Plot-Interaktion

| Geste | Wirkung |
|-------|---------|
| Wischen | Verschieben (ViewBox translate) |
| Doppeltippen | Auto-Range (Zoom zurück) |
| Mausrad (Dev am PC) | Zoom |

Historie: `collections.deque`, max. **3600** Punkte (~1 h @ 1 Hz).

---

## 5. Abhängigkeiten auf dem Pi

| Paket | Zweck | Status Stretch (Stand Test) |
|-------|-------|----------------------------|
| `python3-kivy` | UI | apt 404 (Stretch-Archive) |
| `python3-pyqt5` | PyQtGraph-Backend | apt 404 |
| `pyqtgraph==0.11.1` | Plot | **pip OK** |
| `numpy` | Arrays | vorinstalliert 1.12.1 |
| `spidev` | ADC | vorhanden |

### Installation (empfohlen)

**Option A — Pakete reparieren (Stretch EOL):**

```bash
# /etc/apt/sources.list → archive.debian.org für stretch
sudo apt update
sudo apt install python3-kivy python3-pyqt5
pip3 install pyqtgraph==0.11.1
```

**Option B — OS-Upgrade** auf Bullseye/Bookworm (32-bit): einfachere Kivy/PyQt5-Wheels, bessere TLS für pip.

### Start GUI

```bash
cd /home/pi/py/TempMonitor/dev
export KIVY_BCM_DISPMANX_ID=0
python3 tm_kivy_plot_app.py
```

Nur über SSH ohne Display: schlägt fehl (`no $DISPLAY` / kein EGL) — **am Touchscreen oder mit angeschlossenem LCD starten**.

---

## 6. Deployment (Windows → Pi)

```powershell
scp C:\Users\ritchie\temp_monitor\spi_adc_tm_try4.py raspi:/home/pi/py/TempMonitor/dev/
scp C:\Users\ritchie\temp_monitor\pg_plot_kivy_widget.py raspi:/home/pi/py/TempMonitor/dev/
scp C:\Users\ritchie\temp_monitor\tm_kivy_plot_app.py raspi:/home/pi/py/TempMonitor/dev/
scp C:\Users\ritchie\temp_monitor\ads1118.py raspi:/home/pi/py/TempMonitor/dev/
```

---

## 7. Offene Punkte / nächste Schritte

1. **Python 3.11.11** Build abwarten (Abschnitt 9), dann Kivy/pyqtgraph testen  
2. **Bildschirmumstellung** erst später — aktuell wieder **HDMI** (`ignore_lcd=1`)  
3. Pinch-Zoom (zwei Finger) optional ergänzen  
4. Alle 4 Kanäle gleichzeitig plotten — später  

---

## 8. Referenzen

- [Kivy on Raspberry Pi](https://kivy.org/doc/stable/installation/installation-rpi.html) — `KIVY_BCM_DISPMANX_ID`, mtdev input  
- [PyQtGraph](https://www.pyqtgraph.org/) — PlotWidget, ViewBox  
- Pi `config.txt`: `/boot/config.txt`, Backup `/boot/config.txt.bak-pre-touch`

---

## 9. Python 3.11.11 auf dem Pi (in Arbeit)

Stretch liefert nur Python **3.5.3**; OpenSSL **1.1.0** reicht nicht für Python 3.11 (benötigt ≥ 1.1.1).

**Skript:** `install_python311.sh` (Log: `install_python311.log`)

| Schritt | Ziel |
|---------|------|
| OpenSSL 1.1.1w | `~/local/openssl111` |
| Python 3.11.11 | `~/local/python311` (`python3.11`, `pip3.11`) |
| pip Pakete | kivy, pyqtgraph, PyQt5, numpy |

**Nach Installation:**

```bash
source ~/py/TempMonitor/dev/python311_env.sh
python3.11 --version
python3.11 -m pip list | grep -iE 'kivy|pyqt|graph'
```

Build läuft im Hintergrund (~30–90 min auf Pi 3). Fortschritt:

```bash
tail -f ~/py/TempMonitor/dev/install_python311.log
```

**Hinweis apt:** Stretch-Mirror tot → `archive.debian.org` für Build-Deps (siehe `debian-archive-stretch.list`).

