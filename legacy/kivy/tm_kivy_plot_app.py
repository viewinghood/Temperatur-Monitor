# -*- coding: utf-8 -*-
"""
TempMonitor — Kivy touch UI (legacy).

Superseded by tm_kivy_app.py (Entwurf). Kept for reference.
Run:  python3 tm_kivy_plot_app.py
"""

import collections
import fcntl
import os
import sys
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton

from pg_plot_kivy_widget import PyQtGraphPlotWidget
from spi_adc_tm_try4 import (
    SAMPLE_INTERVAL_S,
    SENSORS,
    TempMonitorAcquisition,
    format_sample_line,
)


MAX_POINTS = 3600
TOUCH_MIN_HEIGHT = dp(56)

# U1 pair (TC1/TC2) = blues, U2 pair (TC3/TC4) = greens, CJC = orange.
SERIES_COLORS = {
    'TC1': '#4fc3f7',
    'TC2': '#0288d1',
    'TC3': '#81c784',
    'TC4': '#388e3c',
    'U1 CJC': '#ffb74d',
    'U2 CJC': '#f57c00',
}


class TraceBar(BoxLayout):
    """One row: TC1–TC4 (independent toggles) + CJC chip temps."""

    def __init__(self, app_ref, **kwargs):
        super(TraceBar, self).__init__(**kwargs)
        self.app_ref = app_ref
        self.orientation = 'horizontal'
        self.spacing = dp(6)
        self.size_hint_y = None
        self.height = TOUCH_MIN_HEIGHT
        self.padding = [dp(8), dp(4)]

        for sensor_def in SENSORS:
            n = sensor_def['sensor']
            btn = ToggleButton(
                text=sensor_def['name'],
                state='down' if n == 1 else 'normal',
                font_size='16sp',
            )
            btn.sensor = n
            btn.bind(state=self._on_tc_state)
            self.add_widget(btn)

        self.cjc_btn = ToggleButton(
            text='Chip-Temp (CJC)',
            state='normal',
            font_size='16sp',
        )
        self.cjc_btn.bind(state=self._on_cjc_state)
        self.add_widget(self.cjc_btn)

    def _on_tc_state(self, btn, state):
        self.app_ref.set_tc_trace(btn.sensor, state == 'down')

    def _on_cjc_state(self, _btn, state):
        self.app_ref.set_cjc_trace(state == 'down')


class TempMonitorApp(App):
    title = 'TempMonitor'

    def build(self):
        Window.clearcolor = (0.08, 0.09, 0.14, 1)

        root = BoxLayout(orientation='vertical', padding=dp(6), spacing=dp(6))

        self.status_label = Label(
            text='Starte Messung …',
            size_hint_y=None,
            height=dp(72),
            font_size='20sp',
            halign='left',
            valign='middle',
        )
        self.status_label.bind(size=self._wrap_status)
        root.add_widget(self.status_label)

        self.plot = PyQtGraphPlotWidget()
        root.add_widget(self.plot)

        hint = Label(
            text='Wischen = verschieben   Doppeltippen = Zoom zurueck',
            size_hint_y=None,
            height=dp(28),
            font_size='14sp',
            color=(0.7, 0.7, 0.75, 1),
        )
        root.add_widget(hint)

        root.add_widget(TraceBar(self))

        self._history = {}
        self._t0 = None
        self._tc_enabled = {1}
        self._cjc_enabled = False
        self._running = True
        self._sample_lock = threading.Lock()
        self._latest = None

        try:
            self._acq = TempMonitorAcquisition()
            self._sync_acq()
        except Exception as exc:
            self.status_label.text = 'SPI/ADC Fehler: {0}'.format(exc)
            self._acq = None
            return root

        self._worker = threading.Thread(target=self._acquisition_loop, daemon=True)
        self._worker.start()
        Clock.schedule_interval(self._poll_samples, 0.2)
        return root

    def _wrap_status(self, instance, value):
        instance.text_size = (value[0] - dp(12), None)

    def _visible_series_names(self):
        names = []
        for sensor_def in SENSORS:
            if sensor_def['sensor'] in self._tc_enabled:
                names.append(sensor_def['name'])
        if self._cjc_enabled:
            names.extend(['U1 CJC', 'U2 CJC'])
        return names

    def _sync_acq(self):
        if self._acq:
            self._acq.set_active(self._tc_enabled, self._cjc_enabled)

    def set_tc_trace(self, sensor, enabled):
        if enabled:
            self._tc_enabled.add(sensor)
        else:
            self._tc_enabled.discard(sensor)
        self._sync_acq()
        Clock.schedule_once(lambda _dt: self._refresh_plot(), 0)

    def set_cjc_trace(self, enabled):
        self._cjc_enabled = enabled
        self._sync_acq()
        Clock.schedule_once(lambda _dt: self._refresh_plot(), 0)

    def _refresh_plot(self):
        visible = self._visible_series_names()
        snapshot = {
            name: list(self._history[name])
            for name in visible
            if name in self._history and self._history[name]
        }
        if snapshot:
            self.plot.set_series_snapshot(
                snapshot, t0=self._t0, colors=SERIES_COLORS)
        else:
            self.plot.clear_series()
            self._t0 = None

    def _acquisition_loop(self):
        while self._running and self._acq:
            t0 = time.time()
            try:
                sample = self._acq.read_once()
                with self._sample_lock:
                    self._latest = sample
            except Exception as exc:
                with self._sample_lock:
                    self._latest = {'error': str(exc)}
            elapsed = time.time() - t0
            wait = SAMPLE_INTERVAL_S - elapsed
            if wait > 0:
                time.sleep(wait)

    def _poll_samples(self, _dt):
        with self._sample_lock:
            sample = self._latest
            self._latest = None
        if not sample:
            return
        if 'error' in sample:
            self.status_label.text = 'Messfehler: {0}'.format(sample['error'])
            return

        self.status_label.text = format_sample_line(sample)

        if not sample.get('series'):
            return

        if self._t0 is None:
            self._t0 = sample['t']

        for name, val in sample['series'].items():
            if name not in self._history:
                self._history[name] = collections.deque(maxlen=MAX_POINTS)
            self._history[name].append((sample['t'], val))

        visible = self._visible_series_names()
        snapshot = {
            name: list(self._history[name])
            for name in visible
            if name in self._history
        }
        self.plot.set_series_snapshot(
            snapshot, t0=self._t0, colors=SERIES_COLORS)

    def on_stop(self):
        self._running = False
        if self._acq:
            self._acq.close()


def _acquire_single_instance_lock():
    """Only one TempMonitor window/process at a time."""
    lock_path = os.path.join('/tmp', 'tm_kivy_plot_app.lock')
    lock_fp = open(lock_path, 'w')
    try:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('TempMonitor laeuft bereits — kein zweites Fenster.', file=sys.stderr)
        return None
    lock_fp.write(str(os.getpid()))
    lock_fp.flush()
    return lock_fp


def main():
    os.environ.setdefault('DISPLAY', ':0')
    os.environ.setdefault('KIVY_BCM_DISPMANX_ID', '0')
    if _acquire_single_instance_lock() is None:
        return 0
    return TempMonitorApp().run()


if __name__ == '__main__':
    sys.exit(main())
