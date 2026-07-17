# TempMonitor — Architektur & App-Mechanik

**Stand:** 2026-07-10  
**Plattform:** Raspberry Pi 3, Raspberry Pi OS Bullseye, `/home/pi/py/TempMonitor/dev/`

---

## Kurzfassung

| UI | Datei | Display | Plot | Status |
|----|-------|---------|------|--------|
| **HDMI (Eizo)** | `tm_pyqt_plot_app.py` | 1280×1024 Desktop | PyQtGraph **OpenGL** | **Produktiv** |
| **7″ Touch (DSI)** | `tm_pyqt_touch_app.py` | 800×448 borderless | PyQtGraph **OpenGL** (shared `StackedPlotWidget`) | **Produktiv** |
| Kivy (alt) | `tm_kivy_app.py` | 7″ Touch | Offscreen-Bitmap-Brücke | Legacy |

Beide PyQt-Apps teilen dieselbe **Hardware-Schicht** (`TempMonitorHwWorker` + SPI), dieselbe **Plot-Logik** (`StackedPlotWidget`) und dieselbe **CSV-Logging-Schicht**.  
**Ein Prozess zur Zeit** — SPI ist exklusiv (`start_*.sh` beendet die andere Instanz).

**Schaubild (PNG):** [`REPORT-app-mechanik.png`](REPORT-app-mechanik.png) — alle Diagramme auf einer Seite.  
Neu erzeugen (Windows, Node/npx): `python build_app_mechanik_png.py`

---

## 1. Systemübersicht — zwei Frontends, ein Backend

```mermaid
flowchart TB
    subgraph Displays["Anzeigen"]
        HDMI["HDMI Eizo\n1280×1024"]
        TOUCH["7″ DSI Touch\n800×448"]
    end

    subgraph Apps["PyQt5 Apps — je 1 Prozess"]
        PYQT["tm_pyqt_plot_app.py\nTempMonitorWindow"]
        TOUCHAPP["tm_pyqt_touch_app.py\nTempMonitorTouchWindow"]
    end

    subgraph Shared["Gemeinsame Module"]
        SPW["StackedPlotWidget\n(PyQtGraph + OpenGL)"]
        WK["TempMonitorHwWorker\n(QThread)"]
        CSV["CsvSampleLogger"]
        CH["tm_channels / tm_settings / tm_status"]
    end

    subgraph HW["Hardware"]
        SPI["TempMonitorAcquisition\nspi_adc_tm_try4.py"]
        AD["ADS1118 U1 + U2"]
    end

    HDMI --> PYQT
    TOUCH --> TOUCHAPP
    PYQT --> SPW
    TOUCHAPP --> SPW
    PYQT --> WK
    TOUCHAPP --> WK
    PYQT --> CSV
    TOUCHAPP --> CSV
    WK --> SPI --> AD

    LEG["tm_kivy_app.py\n(legacy, Bitmap)"] -.-> TOUCH
```

| Startskript | Desktop-Icon |
|-------------|--------------|
| `start_tm_gui.sh` | `TempMonitor.desktop` |
| `start_tm_pyqt_touch_gui.sh` | `TempMonitor-Touch.desktop` |
| `start_tm_kivy_gui.sh` | `TempMonitor-Kivy.desktop` (Legacy) |

Display-Umschaltung: `set_touch_display.sh` (`touch` / `hdmi` / `status`) + Reboot.

---

## 2. Schichten und Threads (PyQt HDMI & Touch)

```mermaid
flowchart TB
    subgraph HT["Hauptthread — QApplication Event-Loop"]
        MW["TempMonitorWindow\noder TempMonitorTouchWindow"]
        SPW["StackedPlotWidget\nuseOpenGL=True"]
        LOG["CsvSampleLogger"]
        BTN["Sidebar / Buttons\nTC, CJC, Logging, ☰"]
        MW --> SPW
        MW --> LOG
        MW --> BTN
    end

    subgraph WT["QThread — Hardware-Loop"]
        HW["TempMonitorHwWorker\n(QObject, moveToThread)"]
    end

    subgraph HWL["SPI / Linux — nur Worker-Thread"]
        ACQ["TempMonitorAcquisition"]
        AD1["ADS1118 U1\nSPI0 CS0"]
        AD2["ADS1118 U2\nSPI0 CS1"]
        ACQ --> AD1
        ACQ --> AD2
    end

    BTN -->|"set_active_channels()"| HW
    HW -->|"sample_ready(list)"| MW
    HW -->|"status_text(str)"| MW
    HW -->|"error(str)"| MW
    HW --> ACQ
    MW -->|"write_packet()"| LOG
    MW -->|"update_histories()"| SPW
```

| Thread | Objekte | Aufgabe |
|--------|---------|---------|
| **Hauptthread** | Fenster, Plot, Logger, Buttons | UI, OpenGL-Plot, CSV, Touch/Maus |
| **QThread** | `TempMonitorHwWorker` | 1-Hz-Messloop, SPI, Signale |

**Regel:** Nur der Worker berührt SPI. UI → Worker nur über `set_active_channels()` (thread-sicher, `QMutex`).

**Touch-Bedienung:** X11 liefert Finger als Maus-Events; Qt-Buttons und PyQtGraph-Pan/Zoom funktionieren nativ (kein Kivy).

---

## 3. OpenGL / Rendering

```mermaid
flowchart LR
    subgraph PyQt["PyQt HDMI + Touch — empfohlen"]
        PG["PyQtGraph\nuseOpenGL=True"]
        GL["QOpenGLWidget\nVideoCore / Mesa"]
        PG --> GL
    end

    subgraph KivyLegacy["Kivy Legacy — nicht empfohlen"]
        OFF["PyQtGraph offscreen\nQT_QPA_PLATFORM=offscreen"]
        GRAB["grab → NumPy → Kivy-Textur"]
        OFF --> GRAB
    end
```

| Pfad | OpenGL | Bemerkung |
|------|--------|-----------|
| `tm_pyqt_plot_app.py` | ✅ `useOpenGL=True` | Aktiv wenn apt-`python3-pyqt5.qtopengl` installiert |
| `tm_pyqt_touch_app.py` | ✅ (importiert `StackedPlotWidget`) | Gleicher Plot-Code |
| `pg_plot_kivy_widget.py` | ❌ | Offscreen ohne GL-Kontext |

Abschalten (Debug): `TM_DISABLE_OPENGL=1 start_tm_gui.sh`

Pi-Check (im dev-Verzeichnis):
```bash
cd ~/py/TempMonitor/dev
python3 -c "import tm_pyqt_plot_app as a; print('OpenGL', a._PG_USE_OPENGL)"
# Erwartung: OpenGL True
```

---

## 4. Touch-UI — Navigation (☰ Toggle)

```mermaid
stateDiagram-v2
    [*] --> PlotAnsicht
    PlotAnsicht --> Einstellungen: ☰ antippen (blau)
    Einstellungen --> PlotAnsicht: ☰ nochmal (dunkel)
    note right of PlotAnsicht
        Hauptansicht — Messung + Plot
        kein separater Plot-Button
    end note
    note right of Einstellungen
        Plot-Zeitfenster, CSV-Missing,
        Display-Umschalt HDMI/Touch
    end note
```

Sidebar (7 Zeilen, gleiche Schriftgröße): TC1–4, Chip CJC, Logging (grün wenn an), ☰.

---

## 5. Programmablauf — Start bis Event-Loop

```mermaid
flowchart TD
    A(["Start: start_tm_*.sh"]) --> B{Lock frei?\n/tmp/tm_*_app.lock}
    B -->|nein| Z([Zweite Instanz beenden])
    B -->|ja| C["QApplication + Fenster"]
    C --> D[Worker → QThread]
    D --> E[Signale verbinden]
    E --> F["thread.start() → worker.run()"]
    F --> G["app.exec()"]

    G --> H{Event}
    H -->|sample_ready| I[Historie + Plot + CSV]
    H -->|status_text| J[Statuszeile]
    H -->|Toggle| K[set_active_channels]
    H -->|Beenden| L[worker.stop, Thread wait]

    I --> G
    J --> G
    K --> G
    L --> M([Ende])
```

---

## 6. Messzyklus (1 Hz) — Sequenzdiagramm

```mermaid
sequenceDiagram
    participant UI as Hauptthread
    participant W as TempMonitorHwWorker
    participant A as TempMonitorAcquisition
    participant SPI as ADS1118 U1/U2

    UI->>W: QThread.started → run()
    W->>A: TempMonitorAcquisition()
    W->>A: set_active(tc_mask, cjc)

    loop alle SAMPLE_INTERVAL_S (1 s)
        W->>A: read_once()
        A->>SPI: TC + CJC
        SPI-->>A: Rohwerte
        A-->>W: sample {t, series}
        W->>W: _sample_to_packet() → 6×(t, temp|None)
        W-->>UI: sample_ready(packet)
        W-->>UI: status_text(...)
        UI->>UI: Historie, OpenGL-Plot, optional CSV
    end

    UI->>W: stop()
    W->>A: close()
    W-->>UI: finished()
```

---

## 7. Signal `sample_ready` — Datenformat

**Typ:** `pyqtSignal(list)` — **6 Einträge**, Index = Kanal.

| Index | Kanal | Hardware |
|-------|-------|----------|
| 0 | TC1 | U1 AIN0–AIN1 |
| 1 | TC2 | U1 AIN2–AIN3 |
| 2 | TC3 | U2 AIN0–AIN1 |
| 3 | TC4 | U2 AIN2–AIN3 |
| 4 | U1 CJC | Chip-Temp U1 |
| 5 | U2 CJC | Chip-Temp U2 |

Jeder Eintrag: **`(zeit_s, temp_c)`** — `temp_c = None` wenn inaktiv/offen.

### Signale & Slots

| Signal / Slot | Richtung | Inhalt |
|---------------|----------|--------|
| `sample_ready` | Worker → UI | 6-Kanal-Paket |
| `status_text` | Worker → UI | z. B. `TC1=28.76°C` |
| `error` | Worker → UI | SPI-Fehler |
| `finished` | Worker → UI | Loop Ende |
| `set_active_channels` | UI → Worker | TC-Maske + CJC |
| `stop()` | UI → Worker | Loop + SPI schließen |

---

## 8. UI-Logik — Kanäle, Plot-Zeit, Logging

```mermaid
flowchart LR
    subgraph Toggle["Kanal Toggle"]
        T1[TC / CJC an/aus]
        T1 --> T2{EIN?}
        T2 -->|ja| T3[Historie löschen]
        T3 --> T4{Andere aktiv?}
        T4 -->|nein| T5[Plot-t0 Reset]
        T4 -->|ja| T6[Spur ab jetzt]
        T2 -->|aus| T7[Spur entfernen]
        T5 --> T8[set_active_channels]
        T6 --> T8
        T7 --> T8
    end

    subgraph Sample["on_sample_ready"]
        S1{reset plot t0?}
        S1 --> S2[Historie + update_histories]
        S2 --> S3{Logging?}
        S3 -->|ja| S4[CSV-Zeile]
    end
```

| Ebene | Variable | Bedeutung |
|-------|----------|-----------|
| Worker | `_t0` | Absoluter Messstart |
| UI-Plot | `_plot_t0` | Anzeige-Offset; Reset wenn alle Kanäle aus waren |
| CSV | Worker-Zeit | Monoton, unabhängig von Plot-Reset |

---

## 9. Modul-Map — Dateien und Rollen

```mermaid
flowchart TB
    subgraph Entry
        SH1[start_tm_gui.sh]
        SH2[start_tm_pyqt_touch_gui.sh]
        APP1[tm_pyqt_plot_app.py]
        APP2[tm_pyqt_touch_app.py]
    end

    subgraph UI_Core
        CH[tm_channels.py]
        ST[tm_status.py]
        SET[tm_settings.py]
        PL[tm_platform.py]
        CSV[tm_csv_logger.py]
        SD[tm_settings_dialog.py]
    end

    subgraph HW
        WK[tm_hw_worker.py]
        SPI[spi_adc_tm_try4.py]
        ADC[ads1118.py]
    end

    subgraph Display
        DM[tm_display_mode.py]
        DS[tm_display_switch.py]
        STD[set_touch_display.sh]
    end

    SH1 --> APP1
    SH2 --> APP2
    APP1 --> WK
    APP2 --> WK
    APP1 --> CSV
    APP2 --> CSV
    APP2 --> DS
    SD --> SET
    CSV --> SET
    WK --> SPI --> ADC
    DS --> STD
```

| Datei | Rolle |
|-------|--------|
| `tm_pyqt_plot_app.py` | HDMI-UI, `StackedPlotWidget`, OpenGL-Config, `TempMonitorWindow` |
| `tm_pyqt_touch_app.py` | Touch-UI 800×448, Sidebar, ☰-Toggle, importiert Plot aus obigem Modul |
| `tm_hw_worker.py` | `TempMonitorHwWorker` — QThread, Signale, Mutex |
| `spi_adc_tm_try4.py` | `TempMonitorAcquisition`, 1 Hz, TC + CJC |
| `ads1118.py` | Low-Level SPI-Treiber |
| `tm_channels.py` | Kanalnamen, Farben, `MAX_HISTORY` |
| `tm_csv_logger.py` | CSV unter `~/tm_log/` |
| `tm_settings.py` / `tm_settings_dialog.py` | Plot-Fenster, Missing-Werte |
| `set_touch_display.sh` | Boot-Config HDMI ↔ Touch |

**Legacy (Referenz):** `tm_kivy_app.py`, `tm_kivy_hw.py`, `tm_kivy_screens.py`, `pg_plot_kivy_widget.py`

---

## 10. CSV-Logging

- Pfad: `~/tm_log/YYYYMMDD-HHMMSS.csv`
- Header: `Time,TC1,TC2,TC3,TC4,U1,U2`
- Start nur wenn ≥1 Sensor aktiv; Stopp wenn letzter Sensor aus oder App-Ende
- Inaktive Spalten während Logging: konfigurierbar (`nan`, `#N/A`, …)

---

## 11. Start / Singleton / SPI-Exklusivität

```bash
# HDMI
~/py/TempMonitor/dev/start_tm_gui.sh

# 7″ Touch
~/py/TempMonitor/dev/start_tm_pyqt_touch_gui.sh
```

| Lock-Datei | App |
|------------|-----|
| `/tmp/tm_pyqt_plot_app.lock` | HDMI |
| `/tmp/tm_pyqt_touch_app.lock` | Touch |
| `/tmp/tm_kivy_app.lock` | Kivy (legacy) |

Touch-Starter beendet automatisch laufende HDMI- oder Kivy-Instanz (SPI freigeben).

---

## 12. Warum PyQt-only statt Kivy-Hybrid?

| Kivy + Bitmap | PyQt-only (aktuell) |
|---------------|---------------------|
| Zwei GUI-Stacks | Eine Qt-Event-Loop |
| Offscreen → Textur (CPU) | OpenGL direkt im Fenster |
| Queue / Clock-Polling | Qt Signals/Slots |
| Touch-Buttons fehleranfällig | Native Qt Touch (= Maus) |

Kivy war sinnvoll auf Stretch ohne Desktop; unter Bullseye + X11 ist **PyQt5 die bessere Wahl** für Touch und HDMI.
