# -*- coding: utf-8 -*-
"""Settings dialog — touch-friendly buttons."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tm_display_mode import (
    display_switch_target,
    is_touch_display_mode,
)
from tm_display_switch import (
    apply_hdmi_switch_and_reboot,
    apply_touch_switch_and_reboot,
)
from tm_platform import log_dir_for_display, os_display_name
from tm_settings import (
    DEFAULT_MISSING_KEY,
    DEFAULT_PLOT_WINDOW_KEY,
    MISSING_LABELS,
    PLOT_WINDOW_LABELS,
)

DIALOG_STYLE = """
QDialog {
    background-color: #1a1a2e;
    color: #eaeaea;
}
QLabel {
    color: #eaeaea;
}
QScrollArea {
    border: none;
    background-color: #1a1a2e;
}
"""

BTN_OPTION_OFF = """
QPushButton {
    background-color: #3a3a4a;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
}
"""

BTN_OPTION_ON = """
QPushButton {
    background-color: #1565c0;
    color: #ffffff;
    border: 1px solid #0d47a1;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-weight: bold;
}
"""

BTN_OK = """
QPushButton {
    background-color: #43a047;
    color: #ffffff;
    border: 1px solid #2e7d32;
    border-radius: 6px;
    padding: 10px 14px;
    font-weight: bold;
}
"""

BTN_CANCEL = """
QPushButton {
    background-color: #3a3a4a;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 6px;
    padding: 10px 14px;
}
"""

BTN_OPTION_DISABLED = """
QPushButton {
    background-color: #2a2a32;
    color: #777777;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-style: italic;
}
"""


class SettingsDialog(QDialog):
    def __init__(
            self,
            current_missing_key=None,
            current_plot_window_key=None,
            parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle('Einstellungen')
        self.setMinimumWidth(480)
        self.setStyleSheet(DIALOG_STYLE)
        current_missing_key = current_missing_key or DEFAULT_MISSING_KEY
        current_plot_window_key = (
            current_plot_window_key or DEFAULT_PLOT_WINDOW_KEY)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll, stretch=1)

        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel('Einstellungen')
        title.setFont(QFont('Sans', 18, QFont.Bold))
        layout.addWidget(title)

        info = QLabel(
            'System: {0}\nLog-Ordner: {1}'.format(
                os_display_name(), log_dir_for_display()))
        info.setFont(QFont('Sans', 12))
        info.setWordWrap(True)
        layout.addWidget(info)

        self._missing_keys = self._add_option_section(
            layout,
            'Kein Messwert in CSV-Logging:',
            MISSING_LABELS,
            current_missing_key)

        self._window_keys = self._add_option_section(
            layout,
            'Plot-Zeitfenster (X-Achse):',
            PLOT_WINDOW_LABELS,
            current_plot_window_key)

        self._add_display_section(layout)

        layout.addStretch(1)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        cancel_btn = QPushButton('Abbrechen')
        cancel_btn.setMinimumHeight(52)
        cancel_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cancel_btn.setFont(QFont('Sans', 14))
        cancel_btn.setStyleSheet(BTN_CANCEL)
        cancel_btn.setFocusPolicy(Qt.NoFocus)
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton('OK')
        ok_btn.setMinimumHeight(52)
        ok_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ok_btn.setFont(QFont('Sans', 14))
        ok_btn.setStyleSheet(BTN_OK)
        ok_btn.setFocusPolicy(Qt.NoFocus)
        ok_btn.clicked.connect(self.accept)

        action_row.addWidget(cancel_btn, stretch=1)
        action_row.addWidget(ok_btn, stretch=1)
        outer.addLayout(action_row)

    def _add_display_section(self, layout):
        section = QLabel('Display')
        section.setFont(QFont('Sans', 14, QFont.Bold))
        layout.addWidget(section)

        state = display_switch_target(is_touch_display_mode())
        on_touch = is_touch_display_mode()
        handler = (
            self._confirm_hdmi_switch if on_touch else self._confirm_touch_switch)

        btn = QPushButton(state['label'])
        btn.setMinimumHeight(52)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setFont(QFont('Sans', 14))
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setEnabled(state['enabled'])
        btn.setStyleSheet(
            BTN_OPTION_OFF if state['enabled'] else BTN_OPTION_DISABLED)
        if state['enabled']:
            btn.clicked.connect(handler)
        layout.addWidget(btn)

        hint = []
        if state['hdmi']:
            hint.append('HDMI erkannt')
        if state['touch']:
            hint.append('Touch-Display erkannt')
        if hint:
            note = QLabel(', '.join(hint))
            note.setFont(QFont('Sans', 11))
            note.setStyleSheet('color: #aaaaaa;')
            layout.addWidget(note)

    def _confirm_hdmi_switch(self):
        self._confirm_display_switch(
            'Display auf HDMI (Eizo) umstellen?\n\n'
            'Der Raspberry Pi startet danach neu.',
            apply_hdmi_switch_and_reboot)

    def _confirm_touch_switch(self):
        self._confirm_display_switch(
            'Display auf 7"-Touch (DSI) umstellen?\n\n'
            'Der Raspberry Pi startet danach neu.',
            apply_touch_switch_and_reboot)

    def _confirm_display_switch(self, message, apply_fn):
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

    def _add_option_section(self, layout, title, options, current_key):
        section = QLabel(title)
        section.setFont(QFont('Sans', 14, QFont.Bold))
        layout.addWidget(section)

        group = QButtonGroup(self)
        group.setExclusive(True)
        keys = []
        for key, label in options:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(52)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFont(QFont('Sans', 14))
            btn.setFocusPolicy(Qt.NoFocus)
            if key == current_key:
                btn.setChecked(True)
            group.addButton(btn)
            keys.append((key, btn))
            layout.addWidget(btn)

        if not any(btn.isChecked() for _, btn in keys):
            keys[0][1].setChecked(True)

        group.buttonToggled.connect(
            lambda _btn, _on: self._update_keys_style(keys))
        self._update_keys_style(keys)
        return keys

    def _update_keys_style(self, keys):
        for _key, btn in keys:
            if btn.isChecked():
                btn.setStyleSheet(BTN_OPTION_ON)
            else:
                btn.setStyleSheet(BTN_OPTION_OFF)

    def _selected_from(self, keys, default):
        for key, btn in keys:
            if btn.isChecked():
                return key
        return default

    def selected_missing_key(self):
        return self._selected_from(self._missing_keys, DEFAULT_MISSING_KEY)

    def selected_plot_window_key(self):
        return self._selected_from(self._window_keys, DEFAULT_PLOT_WINDOW_KEY)

    def selected_key(self):
        """Backward compatible alias."""
        return self.selected_missing_key()
