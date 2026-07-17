# -*- coding: utf-8 -*-
"""
TempMonitor — PyQt5 touch UI (7" DSI, 800x448 below lxpanel).

Native PyQtGraph plot (OpenGL) — no Kivy / no bitmap bridge.
Touch on Pi: X11 maps finger input to Qt mouse events; large NoFocus buttons.

Run:  python3 tm_pyqt_touch_app.py
      ~/py/TempMonitor/dev/start_tm_pyqt_touch_gui.sh
"""

import collections
import fcntl
import os
import sys

from PyQt5.QtCore import Qt, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from tm_app_icon import apply_app_icon
from tm_channels import CHANNEL_NAMES, MAX_HISTORY, NUM_CHANNELS
from tm_csv_logger import CsvSampleLogger
from tm_display_mode import display_switch_target, is_touch_display_mode
from tm_display_switch import (
    apply_hdmi_switch_and_reboot,
    apply_touch_switch_and_reboot,
)
from tm_hw_worker import TempMonitorHwWorker
from tm_platform import log_dir_for_display, os_display_name
from tm_pyqt_plot_app import StackedPlotWidget
from tm_settings import (
    DEFAULT_MISSING_KEY,
    DEFAULT_PLOT_WINDOW_KEY,
    MISSING_LABELS,
    PLOT_WINDOW_LABELS,
    plot_window_seconds,
)
from tm_settings_dialog import (
    BTN_OPTION_DISABLED,
    BTN_OPTION_OFF,
    BTN_OPTION_ON,
    DIALOG_STYLE,
)

TOUCH_W = 800
TOUCH_H = 448
TOUCH_TOP = 30
SIDEBAR_W = 118
SIDEBAR_FONT_PT = 15

_SIDEBAR_FONT = 'font-size: {0}pt; font-weight: bold;'.format(SIDEBAR_FONT_PT)

SIDEBAR_STYLE_OFF = """
QPushButton {{
    {font}
    background-color: #3a3a4a;
    color: #e0e0e0;
    border: none;
    border-radius: 0;
    padding: 6px 4px;
}}
""".format(font=_SIDEBAR_FONT)

SIDEBAR_STYLE_ON = """
QPushButton {{
    {font}
    background-color: #1565c0;
    color: #ffffff;
    border: none;
    border-radius: 0;
    padding: 6px 4px;
}}
""".format(font=_SIDEBAR_FONT)

SIDEBAR_STYLE_OPEN = """
QPushButton {{
    {font}
    background-color: #4fc3f7;
    color: #000000;
    border: none;
    border-radius: 0;
    padding: 6px 4px;
}}
""".format(font=_SIDEBAR_FONT)

SIDEBAR_STYLE_LOG = """
QPushButton {{
    {font}
    background-color: #43a047;
    color: #ffffff;
    border: none;
    border-radius: 0;
    padding: 6px 4px;
}}
""".format(font=_SIDEBAR_FONT)

BTN_STYLE_NAV = """
QPushButton {{
    {font}
    background-color: #38588c;
    color: #ffffff;
    border: none;
    border-radius: 0;
    padding: 6px 4px;
}}
QPushButton:pressed {{
    background-color: #2a4066;
}}
""".format(font=_SIDEBAR_FONT)

BTN_STYLE_NAV_ACTIVE = """
QPushButton {{
    {font}
    background-color: #1a73e8;
    color: #ffffff;
    border: none;
    border-radius: 0;
    padding: 6px 4px;
}}
QPushButton:pressed {{
    background-color: #1558b0;
}}
""".format(font=_SIDEBAR_FONT)
BTN_STYLE_EXIT = """
QPushButton {
    background-color: #8c2e2e;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: bold;
}
"""


class TouchPushButton(QPushButton):
    """Large tap target; never steals keyboard focus (touch-only UI)."""

    def __init__(self, text='', checkable=False, min_h=52, **kwargs):
        super(TouchPushButton, self).__init__(text, **kwargs)
        self.setCheckable(checkable)
        self.setMinimumHeight(min_h)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFont(QFont('Sans', SIDEBAR_FONT_PT, QFont.Bold))
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)


class HamburgerButton(TouchPushButton):
    """Three horizontal bars — no Unicode (Kivy font issue on Pi)."""

    def __init__(self, **kwargs):
        kwargs.setdefault('min_h', 52)
        super(HamburgerButton, self).__init__('', **kwargs)
        self.setToolTip('Einstellungen')

    def paintEvent(self, event):
        super(HamburgerButton, self).paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        pen = QPen(Qt.white, max(2, self.height() // 14))
        painter.setPen(pen)
        w, h = self.width(), self.height()
        pad = w * 0.22
        bar_w = w - 2 * pad
        cx = pad
        cy = h * 0.5
        gap = h * 0.14
        for i in (-1, 0, 1):
            y = cy + i * gap
            painter.drawLine(int(cx), int(y), int(cx + bar_w), int(y))


class TouchSettingsPage(QWidget):
    """Inline settings (stack page) — touch-sized option buttons."""

    def __init__(self, parent_win):
        super(TouchSettingsPage, self).__init__(parent_win)
        self._win = parent_win
        self.setStyleSheet(DIALOG_STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll, stretch=1)

        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setSpacing(8)

        title = QLabel('Einstellungen')
        title.setFont(QFont('Sans', 16, QFont.Bold))
        layout.addWidget(title)

        info = QLabel(
            'System: {0}\nLog: {1}'.format(
                os_display_name(), log_dir_for_display()))
        info.setFont(QFont('Sans', 11))
        info.setWordWrap(True)
        layout.addWidget(info)

        self._window_keys = self._add_section(
            layout, 'Plot-Zeitfenster', PLOT_WINDOW_LABELS,
            parent_win._plot_window_key,
            parent_win._set_plot_window_key)

        self._missing_keys = self._add_section(
            layout, 'Kein Messwert (CSV)', MISSING_LABELS,
            parent_win.logger.missing_key,
            parent_win._set_missing_key)

        self._display_title = QLabel('Display')
        layout.addWidget(self._display_title)
        self._disp_btn = TouchPushButton('', min_h=46)
        layout.addWidget(self._disp_btn)
        self._disp_note = QLabel('')
        self._disp_note.setFont(QFont('Sans', 11))
        self._disp_note.setStyleSheet('color: #aaaaaa;')
        layout.addWidget(self._disp_note)
        self._refresh_display_section()

        layout.addStretch(1)

    def _refresh_display_section(self):
        state = display_switch_target(is_touch_display_mode())
        on_touch = is_touch_display_mode()
        self._disp_btn.setText(state['label'])
        self._disp_btn.setEnabled(state['enabled'])
        self._disp_btn.setStyleSheet(
            BTN_OPTION_OFF if state['enabled'] else BTN_OPTION_DISABLED)
        try:
            self._disp_btn.clicked.disconnect()
        except TypeError:
            pass
        if state['enabled']:
            handler = (
                self._win._confirm_hdmi if on_touch else self._win._confirm_touch)
            self._disp_btn.clicked.connect(handler)

        hint = []
        if state['hdmi']:
            hint.append('HDMI erkannt')
        if state['touch']:
            hint.append('Touch-Display erkannt')
        self._disp_note.setText(', '.join(hint))
        self._disp_note.setVisible(bool(hint))

    def _add_section(self, layout, title, options, current_key, apply_fn):
        layout.addWidget(QLabel(title))
        keys = []
        for key, label in options:
            btn = TouchPushButton(label, checkable=True, min_h=46)
            btn.setChecked(key == current_key)
            btn.clicked.connect(
                lambda _on=False, k=key, b=btn, ks=keys: self._pick(k, b, ks, apply_fn))
            layout.addWidget(btn)
            keys.append((key, btn))
        self._sync_keys(keys)
        return keys

    def _pick(self, key, btn, keys, apply_fn):
        if not btn.isChecked():
            btn.setChecked(True)
            return
        for k, b in keys:
            b.blockSignals(True)
            b.setChecked(k == key)
            b.blockSignals(False)
        self._sync_keys(keys)
        apply_fn(key)

    def _sync_keys(self, keys):
        for _key, btn in keys:
            btn.setStyleSheet(BTN_OPTION_ON if btn.isChecked() else BTN_OPTION_OFF)


class TempMonitorTouchWindow(QMainWindow):
    def __init__(self):
        super(TempMonitorTouchWindow, self).__init__()
        self.setWindowTitle('Touch TempMonitor')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(TOUCH_W, TOUCH_H)
        self.move(0, TOUCH_TOP)

        self._histories = {
            name: collections.deque(maxlen=MAX_HISTORY) for name in CHANNEL_NAMES}
        self._active = [True, False, False, False, False, False]
        self._connected = [False] * NUM_CHANNELS
        self._logger = CsvSampleLogger()
        self._status_base = ''
        self._plot_t0 = 0.0
        self._reset_plot_t0 = False
        self._plot_window_key = DEFAULT_PLOT_WINDOW_KEY

        root = QWidget()
        self.setCentralWidget(root)
        root.setStyleSheet('background-color: #1a1a2e;')
        hbox = QHBoxLayout(root)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)

        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(0, 2, 0, 2)
        sidebar.setSpacing(1)
        sidebar_w = QWidget()
        sidebar_w.setFixedWidth(SIDEBAR_W)
        sidebar_w.setLayout(sidebar)

        self._buttons = []
        for i, name in enumerate(CHANNEL_NAMES[:4]):
            btn = TouchPushButton(name, checkable=True, min_h=48)
            btn.setChecked(i == 0)
            btn.toggled.connect(lambda on, idx=i: self._on_tc_toggle(idx, on))
            sidebar.addWidget(btn, stretch=1)
            self._buttons.append(btn)

        self._cjc_btn = TouchPushButton('Chip CJC', checkable=True, min_h=48)
        self._cjc_btn.toggled.connect(self._on_cjc_toggle)
        sidebar.addWidget(self._cjc_btn, stretch=1)

        self._log_btn = TouchPushButton('Logging', checkable=True, min_h=48)
        self._log_btn.toggled.connect(self._on_logging_toggle)
        sidebar.addWidget(self._log_btn, stretch=1)

        self._menu_btn = HamburgerButton()
        self._menu_btn.setCheckable(True)
        self._menu_btn.setChecked(False)
        self._menu_btn.setStyleSheet(BTN_STYLE_NAV)
        self._menu_btn.toggled.connect(self._on_settings_toggle)
        sidebar.addWidget(self._menu_btn, stretch=1)

        hbox.addWidget(sidebar_w)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right_w = QWidget()
        right_w.setLayout(right)
        hbox.addWidget(right_w, stretch=1)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(4, 2, 4, 2)
        self._status = QLabel('Starte Messung …')
        self._status.setFont(QFont('Sans', 12))
        self._status.setWordWrap(True)
        self._status.setStyleSheet('color: #eaeaea; padding: 2px;')
        status_row.addWidget(self._status, stretch=1)

        exit_btn = TouchPushButton('Beenden', min_h=32)
        exit_btn.setFixedWidth(90)
        exit_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        exit_btn.setStyleSheet(BTN_STYLE_EXIT)
        exit_btn.clicked.connect(self.close)
        status_row.addWidget(exit_btn)
        right.addLayout(status_row)

        self._stack = QStackedWidget()
        self._plot = StackedPlotWidget()
        self._settings_page = TouchSettingsPage(self)
        self._stack.addWidget(self._plot)
        self._stack.addWidget(self._settings_page)
        right.addWidget(self._stack, stretch=1)

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

        self._plot.set_active_mask(self._active)
        self._push_channel_config()
        self._update_button_styles()
        self._thread.start()

    @property
    def logger(self):
        return self._logger

    def _on_settings_toggle(self, on):
        """☰ toggles settings panel; second tap returns to plot (no extra Plot button)."""
        if on:
            self._settings_page._refresh_display_section()
            self._stack.setCurrentWidget(self._settings_page)
            self._menu_btn.setStyleSheet(BTN_STYLE_NAV_ACTIVE)
        else:
            self._stack.setCurrentWidget(self._plot)
            self._menu_btn.setStyleSheet(BTN_STYLE_NAV)

    def _close_settings(self):
        if self._menu_btn.isChecked():
            self._menu_btn.blockSignals(True)
            self._menu_btn.setChecked(False)
            self._menu_btn.blockSignals(False)
            self._on_settings_toggle(False)

    def _set_plot_window_key(self, key):
        self._plot_window_key = key
        self._refresh_plot()

    def _set_missing_key(self, key):
        self._logger.set_missing_key(key)

    def _confirm_hdmi(self):
        self._confirm_reboot(
            'Display auf HDMI (Eizo) umstellen?\n\nDer Raspberry Pi startet neu.',
            apply_hdmi_switch_and_reboot)

    def _confirm_touch(self):
        self._confirm_reboot(
            'Display auf 7"-Touch (DSI) umstellen?\n\nDer Raspberry Pi startet neu.',
            apply_touch_switch_and_reboot)

    def _confirm_reboot(self, message, apply_fn):
        box = QMessageBox(self)
        box.setWindowTitle('Bestaetigen')
        box.setText(message)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        box.setStyleSheet(DIALOG_STYLE)
        for btn in box.buttons():
            btn.setMinimumHeight(48)
            btn.setMinimumWidth(120)
            btn.setFocusPolicy(Qt.NoFocus)
        if box.exec_() == QMessageBox.Yes:
            apply_fn()

    def _update_button_styles(self):
        for i, btn in enumerate(self._buttons):
            if not btn.isChecked():
                btn.setStyleSheet(SIDEBAR_STYLE_OFF)
            elif self._connected[i]:
                btn.setStyleSheet(SIDEBAR_STYLE_ON)
            else:
                btn.setStyleSheet(SIDEBAR_STYLE_OPEN)
        if not self._cjc_btn.isChecked():
            self._cjc_btn.setStyleSheet(SIDEBAR_STYLE_OFF)
        elif self._connected[4] or self._connected[5]:
            self._cjc_btn.setStyleSheet(SIDEBAR_STYLE_ON)
        else:
            self._cjc_btn.setStyleSheet(SIDEBAR_STYLE_OPEN)
        if self._log_btn.isChecked():
            self._log_btn.setStyleSheet(SIDEBAR_STYLE_LOG)
        else:
            self._log_btn.setStyleSheet(SIDEBAR_STYLE_OFF)

    def _active_mask(self):
        mask = [self._buttons[i].isChecked() for i in range(4)]
        cjc = self._cjc_btn.isChecked()
        mask.extend([cjc, cjc])
        return mask

    def _other_channels_active(self, skip_tc_idx=None, skip_cjc=False):
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
        self._update_button_styles()
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

    def _on_tc_toggle(self, idx, checked):
        if checked:
            self._histories[CHANNEL_NAMES[idx]].clear()
            self._connected[idx] = False
            self._maybe_reset_plot_time(checked, skip_tc_idx=idx)
        self._push_channel_config()

    def _on_cjc_toggle(self, checked):
        if checked:
            self._histories['U1 CJC'].clear()
            self._histories['U2 CJC'].clear()
            self._connected[4] = False
            self._connected[5] = False
            self._maybe_reset_plot_time(checked, skip_cjc=True)
        self._push_channel_config()

    def _on_logging_toggle(self, checked):
        if checked:
            if not self._any_sensor_active():
                self._log_btn.blockSignals(True)
                self._log_btn.setChecked(False)
                self._log_btn.blockSignals(False)
                self._update_button_styles()
                return
            path = self._logger.start()
            self._on_status_text(self._status_base)
            self._status.setText(
                self._status_base + '   |   Logging: {0}'.format(path))
        else:
            self._stop_logging(update_button=False)
        self._update_button_styles()

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
            self._histories[CHANNEL_NAMES[i]].append(
                (t_sec - self._plot_t0, temp_c))
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
        super(TempMonitorTouchWindow, self).closeEvent(event)


def _acquire_single_instance_lock():
    lock_path = '/tmp/tm_pyqt_touch_app.lock'
    lock_fp = open(lock_path, 'w')
    try:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('TempMonitor Touch laeuft bereits.', file=sys.stderr)
        return None
    lock_fp.write(str(os.getpid()))
    lock_fp.flush()
    return lock_fp


def main():
    os.environ.setdefault('DISPLAY', ':0')
    if _acquire_single_instance_lock() is None:
        return 0
    QApplication.setAttribute(Qt.AA_SynthesizeMouseForUnhandledTouchEvents, True)
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = TempMonitorTouchWindow()
    apply_app_icon(app, win, 'TempMonitor-Touch')
    win.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
