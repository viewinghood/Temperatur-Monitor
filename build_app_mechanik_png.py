# -*- coding: utf-8 -*-
"""Render REPORT-app-design mermaid diagrams and stitch one PNG poster."""

import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(ROOT, 'docs', 'reports', 'REPORT-app-mechanik.png')

DIAGRAMS = [
    ('1 — System: HDMI + Touch + gemeinsames Backend', r'''
flowchart TB
    subgraph Displays["Anzeigen"]
        HDMI["HDMI Eizo"]
        TOUCH["7 inch DSI Touch"]
    end
    subgraph Apps["PyQt5 Apps"]
        PYQT["tm_pyqt_plot_app.py"]
        TAPP["tm_pyqt_touch_app.py"]
    end
    subgraph Shared["Gemeinsam"]
        SPW["StackedPlotWidget OpenGL"]
        WK["TempMonitorHwWorker"]
        CSV["CsvSampleLogger"]
    end
    subgraph HW["SPI"]
        ACQ["TempMonitorAcquisition"]
        AD["ADS1118 U1+U2"]
    end
    HDMI --> PYQT
    TOUCH --> TAPP
    PYQT --> SPW
    TAPP --> SPW
    PYQT --> WK
    TAPP --> WK
    WK --> ACQ --> AD
'''),
    ('2 — Schichten und Threads', r'''
flowchart TB
    subgraph HT["Hauptthread QApplication"]
        MW["TempMonitorWindow / TouchWindow"]
        SPW["StackedPlotWidget"]
        LOG["CsvSampleLogger"]
        BTN["Buttons Sidebar"]
        MW --> SPW
        MW --> LOG
        MW --> BTN
    end
    subgraph WT["QThread"]
        HW["TempMonitorHwWorker"]
    end
    subgraph HWL["SPI nur Worker"]
        ACQ["TempMonitorAcquisition"]
        AD1["ADS1118 U1"]
        AD2["ADS1118 U2"]
        ACQ --> AD1
        ACQ --> AD2
    end
    BTN -->|"set_active_channels"| HW
    HW -->|"sample_ready"| MW
    HW --> ACQ
    MW -->|"update_histories"| SPW
'''),
    ('3 — OpenGL vs Kivy Legacy', r'''
flowchart LR
    subgraph PyQt["PyQt HDMI + Touch"]
        PG["PyQtGraph useOpenGL=True"]
        GL["GPU OpenGL"]
        PG --> GL
    end
    subgraph Kivy["Kivy Legacy"]
        OFF["offscreen grab"]
        TEX["Kivy Textur CPU"]
        OFF --> TEX
    end
'''),
    ('4 — Touch: Einstellungen Toggle', r'''
stateDiagram-v2
    [*] --> Plot
    Plot --> Settings: Hamburger an
    Settings --> Plot: Hamburger aus
'''),
    ('5 — Messzyklus 1 Hz', r'''
sequenceDiagram
    participant UI as Hauptthread
    participant W as HwWorker
    participant A as Acquisition
    participant SPI as ADS1118
    loop jede Sekunde
        W->>A: read_once()
        A->>SPI: TC + CJC
        SPI-->>A: Werte
        W-->>UI: sample_ready
        UI->>UI: Plot OpenGL + CSV
    end
'''),
    ('6 — Modul-Map', r'''
flowchart TB
    SH1[start_tm_gui.sh] --> APP1[tm_pyqt_plot_app.py]
    SH2[start_tm_pyqt_touch_gui.sh] --> APP2[tm_pyqt_touch_app.py]
    APP1 --> WK[tm_hw_worker.py]
    APP2 --> WK
    WK --> SPI[spi_adc_tm_try4.py]
    SPI --> ADC[ads1118.py]
    APP1 --> CSV[tm_csv_logger.py]
    APP2 --> CSV
'''),
]


def _run_mmdc(mmd_path, png_path):
    npx = r'C:\Program Files\nodejs\npx.cmd'
    if not os.path.isfile(npx):
        npx = 'npx'
    cmd = [
        npx, '-y', '@mermaid-js/mermaid-cli',
        '-i', mmd_path,
        '-o', png_path,
        '-b', 'white',
        '-w', '1400',
    ]
    subprocess.run(cmd, check=True, cwd=ROOT, shell=(os.name == 'nt'))


def _load_font(size, bold=False):
    candidates = [
        'C:/Windows/Fonts/segoeui.ttf',
        'C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf',
        'C:/Windows/Fonts/arial.ttf',
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
    return ImageFont.load_default()


def main():
    png_paths = []
    with tempfile.TemporaryDirectory() as tmp:
        for idx, (title, src) in enumerate(DIAGRAMS):
            mmd = os.path.join(tmp, 'd{0}.mmd'.format(idx))
            png = os.path.join(tmp, 'd{0}.png'.format(idx))
            with open(mmd, 'w', encoding='utf-8') as fp:
                fp.write(src.strip() + '\n')
            print('Rendering:', title)
            _run_mmdc(mmd, png)
            png_paths.append((title, png))

        title_font = _load_font(36, bold=True)
        section_font = _load_font(22, bold=True)
        margin = 40
        gap = 24
        header_h = 90

        sections = []
        max_w = 0
        total_h = margin + header_h
        for title, path in png_paths:
            img = Image.open(path).convert('RGB')
            sections.append((title, img))
            max_w = max(max_w, img.width)
            total_h += 36 + img.height + gap

        canvas_w = max_w + 2 * margin
        canvas_h = total_h + margin
        canvas = Image.new('RGB', (canvas_w, canvas_h), 'white')
        draw = ImageDraw.Draw(canvas)

        draw.text(
            (margin, margin),
            'TempMonitor — Architektur 2026-07-10',
            fill='#1a1a2e',
            font=title_font)

        y = margin + header_h
        for title, img in sections:
            draw.text((margin, y), title, fill='#1565c0', font=section_font)
            y += 36
            x = margin + (max_w - img.width) // 2
            canvas.paste(img, (x, y))
            y += img.height + gap

        canvas.save(OUT_PATH, 'PNG', optimize=True)
        print('Saved:', OUT_PATH)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print('mermaid-cli failed:', exc, file=sys.stderr)
        sys.exit(1)
