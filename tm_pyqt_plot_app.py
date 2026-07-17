# -*- coding: utf-8 -*-
"""
TempMonitor — native PyQt5 + PyQtGraph UI.

Hardware runs in a QThread (TempMonitorHwWorker); plot updates via signals/slots.
Run:  python3 tm_pyqt_plot_app.py   or  ~/py/TempMonitor/dev/start_tm_gui.sh
"""

import collections
import fcntl
import os
import sys

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QThread, pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tm_channels import CHANNEL_COLORS, CHANNEL_NAMES, MAX_HISTORY, NUM_CHANNELS
from tm_csv_logger import CsvSampleLogger
from tm_hw_worker import TempMonitorHwWorker
from tm_settings import DEFAULT_PLOT_WINDOW_KEY, plot_window_seconds
from tm_settings_dialog import SettingsDialog
from tm_app_icon import apply_app_icon


def _configure_pyqtgraph():
    """Enable GPU plot path when Qt OpenGL is available (apt PyQt5 on Bullseye)."""
    base = dict(
        antialias=True,
        background='#1a1a2e',
        foreground='#eaeaea',
    )
    if os.environ.get('TM_DISABLE_OPENGL', '').strip().lower() in ('1', 'true', 'yes'):
        pg.setConfigOptions(**base)
        return False
    try:
        pg.setConfigOptions(useOpenGL=True, **base)
        return True
    except Exception:
        pg.setConfigOptions(**base)
        return False


_PG_USE_OPENGL = _configure_pyqtgraph()

LEFT_AXIS_WIDTH = 58
Y_DEFAULT_CJC = (25.0, 50.0)
Y_DEFAULT_TC = (0.0, 120.0)
Y_HALF_SPAN_C = 1.0
Y_STEADY_MAX_SPAN_C = 2.0
Y_SPIKE_PADDING_C = 0.5

BTN_STYLE_OFF = """
QPushButton {
    background-color: #3a3a4a;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 6px;
    padding: 6px 10px;
}
"""

BTN_STYLE_ON_CONNECTED = """
QPushButton {
    background-color: #1565c0;
    color: #ffffff;
    border: 1px solid #0d47a1;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: bold;
}
"""

BTN_STYLE_ON_OPEN = """
QPushButton {
    background-color: #4fc3f7;
    color: #000000;
    border: 1px solid #29b6f6;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: bold;
}
"""

BTN_STYLE_LOGGING_ON = """
QPushButton {
    background-color: #43a047;
    color: #ffffff;
    border: 1px solid #2e7d32;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: bold;
}
"""


class StackedPlotWidget(pg.GraphicsLayoutWidget):
    """One stacked row per active channel; shared linked time axis."""

    def __init__(self, parent=None):
        super(StackedPlotWidget, self).__init__(parent)
        self.setBackground('#1a1a2e')
        self._rows = {}
        self._active = [False] * NUM_CHANNELS

    def set_active_mask(self, active):
        active = list(active)
        if active == self._active:
            return
        self._active = active
        self._rebuild()

    def _y_range_for(self, name, y_values=None):
        if y_values is not None and len(y_values) > 0:
            y_min = float(np.min(y_values))
            y_max = float(np.max(y_values))
            span = y_max - y_min
            if span <= Y_STEADY_MAX_SPAN_C:
                mean = float(np.mean(y_values))
                return (mean - Y_HALF_SPAN_C, mean + Y_HALF_SPAN_C)
            pad = max(Y_SPIKE_PADDING_C, span * 0.05)
            return (y_min - pad, y_max + pad)
        if name.endswith('CJC'):
            return Y_DEFAULT_CJC
        return Y_DEFAULT_TC

    def _rebuild(self):
        self.clear()
        self._rows = {}
        names = [CHANNEL_NAMES[i] for i in range(NUM_CHANNELS) if self._active[i]]
        if not names:
            return
        first_plot = None
        for row, name in enumerate(names):
            plot = self.addPlot(row=row, col=0)
            plot.showAxis('top', False)
            plot.showAxis('right', False)
            plot.setMenuEnabled(False)
            plot.getViewBox().setMouseEnabled(x=True, y=True)
            color = CHANNEL_COLORS.get(name, '#eaeaea')
            left = plot.getAxis('left')
            left.setWidth(LEFT_AXIS_WIDTH)
            left.setStyle(tickTextOffset=4)
            plot.setLabel('left', name, units='°C', color=color)
            y0, y1 = self._y_range_for(name)
            plot.setYRange(y0, y1, padding=0)
            plot.getViewBox().disableAutoRange(axis=pg.ViewBox.YAxis)
            plot.showGrid(x=True, y=True, alpha=0.25)
            bottom = plot.getAxis('bottom')
            if row < len(names) - 1:
                bottom.setStyle(showValues=False)
                bottom.setHeight(18)
            else:
                plot.setLabel('bottom', 'Zeit (s)')
            curve = plot.plot([], [], pen=pg.mkPen(color=color, width=2))
            self._rows[name] = {'plot': plot, 'curve': curve}
            if first_plot is None:
                first_plot = plot
            else:
                plot.setXLink(first_plot)

    def update_histories(self, histories, window_sec=None):
        """histories: dict name -> list of (t, temp|None). window_sec=None => full range."""
        names = [CHANNEL_NAMES[i] for i in range(NUM_CHANNELS) if self._active[i]]
        if not names:
            return
        if set(names) != set(self._rows.keys()):
            self._rebuild()

        x_max = 0.0
        for name in names:
            for t, _val in histories.get(name, []):
                if t > x_max:
                    x_max = t

        if window_sec is not None and window_sec > 0:
            x_min = max(0.0, x_max - float(window_sec))
            x_end = max(x_min + 1.0, x_max) if x_max > x_min else max(5.0, x_max)
        else:
            x_min = 0.0
            x_end = max(5.0, x_max)

        for name in names:
            points = histories.get(name, [])
            xs = []
            ys = []
            for t, val in points:
                if t < x_min:
                    continue
                if val is None:
                    continue
                xs.append(t)
                ys.append(val)
            x = np.asarray(xs, dtype=np.float64)
            y = np.asarray(ys, dtype=np.float64)
            plot = self._rows[name]['plot']
            vb = plot.getViewBox()
            if x.size == 0:
                self._rows[name]['curve'].setData([], [])
                y0, y1 = self._y_range_for(name)
            else:
                if x.size == 1:
                    x = np.array([x[0], x[0] + 0.01], dtype=np.float64)
                    y = np.array([y[0], y[0]], dtype=np.float64)
                self._rows[name]['curve'].setData(x, y)
                y0, y1 = self._y_range_for(name, y)
            vb.disableAutoRange(axis=pg.ViewBox.YAxis)
            vb.setYRange(y0, y1, padding=0)

        for name in names:
            self._rows[name]['plot'].getViewBox().setXRange(
                x_min, x_end, padding=0.02)


class TempMonitorWindow(QMainWindow):
    def __init__(self):
        super(TempMonitorWindow, self).__init__()
        self.setWindowTitle('HDMI TempMonitor')
        self.resize(1024, 768)

        self._histories = {
            name: collections.deque(maxlen=MAX_HISTORY) for name in CHANNEL_NAMES}
        self._active = [True, False, False, False, False, False]
        self._connected = [False] * NUM_CHANNELS
        self._logger = CsvSampleLogger()
        self._status_base = ''
        self._plot_t0 = 0.0
        self._reset_plot_t0 = False
        self._plot_window_key = DEFAULT_PLOT_WINDOW_KEY

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._status = QLabel('Starte Messung …')
        self._status.setFont(QFont('Sans', 12))
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._plot = StackedPlotWidget()
        layout.addWidget(self._plot, stretch=1)

        hint = QLabel('Mausrad = Zoom   Doppelklick = Zoom zurueck')
        hint.setStyleSheet('color: #aaa;')
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 0, 0, 0)
        self._buttons = []
        for i, name in enumerate(CHANNEL_NAMES[:4]):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setMinimumHeight(48)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFont(QFont('Sans', 14))
            btn.toggled.connect(lambda checked, idx=i: self._on_tc_toggle(idx, checked))
            btn_row.addWidget(btn, stretch=1)
            self._buttons.append(btn)

        self._cjc_btn = QPushButton('Chip CJC')
        self._cjc_btn.setCheckable(True)
        self._cjc_btn.setMinimumHeight(48)
        self._cjc_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._cjc_btn.setFont(QFont('Sans', 14))
        self._cjc_btn.toggled.connect(self._on_cjc_toggle)
        btn_row.addWidget(self._cjc_btn, stretch=1)

        self._log_btn = QPushButton('Logging')
        self._log_btn.setCheckable(True)
        self._log_btn.setMinimumHeight(48)
        self._log_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._log_btn.setFont(QFont('Sans', 14))
        self._log_btn.setStyleSheet(BTN_STYLE_OFF)
        self._log_btn.toggled.connect(self._on_logging_toggle)
        btn_row.addWidget(self._log_btn, stretch=1)

        self._settings_btn = QPushButton('\u2630')
        self._settings_btn.setToolTip('Einstellungen')
        self._settings_btn.setMinimumHeight(48)
        self._settings_btn.setFixedWidth(52)
        self._settings_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._settings_btn.setFont(QFont('Sans', 18))
        self._settings_btn.setStyleSheet(BTN_STYLE_OFF)
        self._settings_btn.clicked.connect(self._open_settings)
        btn_row.addWidget(self._settings_btn, stretch=0)

        layout.addLayout(btn_row)

        self._plot.set_active_mask(self._active)

        self._thread = QThread()
        self._worker = TempMonitorHwWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.sample_ready.connect(self.on_sample_ready)
        self._worker.status_text.connect(self._on_status_text)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._push_channel_config()
        self._update_button_styles()
        self._thread.start()

    def _update_button_styles(self):
        for i, btn in enumerate(self._buttons):
            if not btn.isChecked():
                btn.setStyleSheet(BTN_STYLE_OFF)
            elif self._connected[i]:
                btn.setStyleSheet(BTN_STYLE_ON_CONNECTED)
            else:
                btn.setStyleSheet(BTN_STYLE_ON_OPEN)
        if not self._cjc_btn.isChecked():
            self._cjc_btn.setStyleSheet(BTN_STYLE_OFF)
        elif self._connected[4] or self._connected[5]:
            self._cjc_btn.setStyleSheet(BTN_STYLE_ON_CONNECTED)
        else:
            self._cjc_btn.setStyleSheet(BTN_STYLE_ON_OPEN)

    def _active_mask(self):
        mask = [self._buttons[i].isChecked() for i in range(4)]
        mask.append(self._cjc_btn.isChecked())
        mask.append(self._cjc_btn.isChecked())
        return mask

    def _other_channels_active(self, skip_tc_idx=None, skip_cjc=False):
        """True if any channel other than the one being toggled on is active."""
        for i in range(4):
            if skip_tc_idx is not None and i == skip_tc_idx:
                continue
            if self._buttons[i].isChecked():
                return True
        if not skip_cjc and self._cjc_btn.isChecked():
            return True
        return False

    def _maybe_reset_plot_time(self, checked, skip_tc_idx=None, skip_cjc=False):
        if checked and not self._other_channels_active(skip_tc_idx, skip_cjc):
            self._reset_plot_t0 = True

    def _any_sensor_active(self):
        return any(self._buttons[i].isChecked() for i in range(4)) or self._cjc_btn.isChecked()

    def _stop_logging(self, update_button=True):
        self._logger.stop()
        if update_button:
            self._log_btn.blockSignals(True)
            self._log_btn.setChecked(False)
            self._log_btn.blockSignals(False)
            self._log_btn.setStyleSheet(BTN_STYLE_OFF)
        self._on_status_text(self._status_base)

    def _push_channel_config(self):
        tc_mask = [self._buttons[i].isChecked() for i in range(4)]
        self._active = self._active_mask()
        self._worker.set_active_channels(tc_mask, self._cjc_btn.isChecked())
        self._plot.set_active_mask(self._active)
        self._update_button_styles()
        self._refresh_plot()
        if self._logger.enabled and not self._any_sensor_active():
            self._stop_logging()

    def _clear_trace(self, name, channel_idx=None):
        self._histories[name].clear()
        if channel_idx is not None:
            self._connected[channel_idx] = False

    def _on_tc_toggle(self, idx, checked):
        if checked:
            self._clear_trace(CHANNEL_NAMES[idx], channel_idx=idx)
            self._maybe_reset_plot_time(checked, skip_tc_idx=idx)
        self._push_channel_config()

    def _on_cjc_toggle(self, checked):
        if checked:
            self._clear_trace('U1 CJC', channel_idx=4)
            self._clear_trace('U2 CJC', channel_idx=5)
            self._maybe_reset_plot_time(checked, skip_cjc=True)
        self._push_channel_config()

    def _on_logging_toggle(self, checked):
        if checked:
            if not self._any_sensor_active():
                self._log_btn.blockSignals(True)
                self._log_btn.setChecked(False)
                self._log_btn.blockSignals(False)
                return
            path = self._logger.start()
            self._log_btn.setStyleSheet(BTN_STYLE_LOGGING_ON)
            self._on_status_text(self._status_base)
            self._status.setText(
                self._status_base + '   |   Logging: {0}'.format(path))
        else:
            self._stop_logging(update_button=False)
            self._log_btn.setStyleSheet(BTN_STYLE_OFF)

    def _open_settings(self):
        dlg = SettingsDialog(
            self._logger.missing_key,
            self._plot_window_key,
            self)
        if dlg.exec_():
            self._logger.set_missing_key(dlg.selected_missing_key())
            self._plot_window_key = dlg.selected_plot_window_key()
            self._refresh_plot()

    @pyqtSlot(str)
    def _on_status_text(self, text):
        self._status_base = text
        if self._logger.enabled and self._logger.path:
            self._status.setText(
                text + '   |   Logging: {0}'.format(self._logger.path))
        else:
            self._status.setText(text)

    @pyqtSlot(list)
    def on_sample_ready(self, packet):
        """packet: 6 x (time_s, temp_c|None)."""
        if not packet:
            return
        if self._reset_plot_t0:
            self._plot_t0 = packet[0][0]
            self._reset_plot_t0 = False
        tc_mask = [self._buttons[i].isChecked() for i in range(4)]
        cjc_on = self._cjc_btn.isChecked()
        if self._logger.enabled:
            self._logger.write_packet(packet, tc_mask, cjc_on)
        for i, (t_sec, temp_c) in enumerate(packet):
            if i < 4:
                if self._active[i]:
                    self._connected[i] = temp_c is not None
            elif cjc_on and temp_c is not None:
                self._connected[i] = True
            if not self._active[i]:
                continue
            name = CHANNEL_NAMES[i]
            self._histories[name].append((t_sec - self._plot_t0, temp_c))
        self._update_button_styles()
        self._refresh_plot()

    def _refresh_plot(self):
        visible = {
            CHANNEL_NAMES[i]: list(self._histories[CHANNEL_NAMES[i]])
            for i in range(NUM_CHANNELS)
            if self._active[i]
        }
        self._plot.update_histories(
            visible, plot_window_seconds(self._plot_window_key))

    @pyqtSlot(str)
    def _on_error(self, message):
        self._status.setText('Fehler: {0}'.format(message))

    def closeEvent(self, event):
        self._logger.stop()
        self._worker.stop()
        self._thread.quit()
        self._thread.wait(4000)
        super(TempMonitorWindow, self).closeEvent(event)


def _acquire_single_instance_lock():
    lock_path = '/tmp/tm_pyqt_plot_app.lock'
    lock_fp = open(lock_path, 'w')
    try:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('TempMonitor laeuft bereits.', file=sys.stderr)
        return None
    lock_fp.write(str(os.getpid()))
    lock_fp.flush()
    return lock_fp


def main():
    os.environ.setdefault('DISPLAY', ':0')
    if _acquire_single_instance_lock() is None:
        return 0
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = TempMonitorWindow()
    apply_app_icon(app, win, 'TempMonitor')
    win.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
