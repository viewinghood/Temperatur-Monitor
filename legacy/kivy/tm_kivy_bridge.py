# -*- coding: utf-8 -*-
"""Qt signal bridge — worker QThread to Kivy main thread."""

from kivy.clock import Clock
from PyQt5.QtCore import QObject, pyqtSlot


class QtToKivyBridge(QObject):
    """Receives pyqt signals on the Qt main thread, forwards to Kivy Clock."""

    def __init__(self, kivy_app, **kwargs):
        super(QtToKivyBridge, self).__init__(**kwargs)
        self._app = kivy_app

    @pyqtSlot(list)
    def on_sample_ready(self, packet):
        Clock.schedule_once(lambda _dt: self._app._handle_sample(packet), 0)

    @pyqtSlot(str)
    def on_status_text(self, text):
        Clock.schedule_once(lambda _dt: self._app._set_status_base(text), 0)

    @pyqtSlot(str)
    def on_error(self, message):
        Clock.schedule_once(
            lambda _dt: self._app._show_error(message), 0)
