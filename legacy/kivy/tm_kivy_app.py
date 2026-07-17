# -*- coding: utf-8 -*-
"""
TempMonitor — Kivy touch UI, left sidebar (800x454 below panel).

Run:  python3 tm_kivy_app.py
      ~/py/TempMonitor/dev/start_tm_kivy_gui.sh
"""

import collections
import fcntl
import os
import sys

# Kivy window geometry — must be set before other kivy imports (800x454 below lxpanel).
if os.path.isfile(os.path.expanduser('~/.config/tm_kivy_display.env')):
    os.environ.setdefault('KIVY_BCM_DISPMANX_ID', '0')
    from kivy.config import Config
    Config.set('kivy', 'exit_on_escape', '0')
    Config.set('graphics', 'borderless', '1')
    Config.set('graphics', 'width', '800')
    Config.set('graphics', 'height', '448')
    Config.set('graphics', 'position', 'custom')
    Config.set('graphics', 'top', '30')
    Config.set('graphics', 'left', '0')
    Config.set('graphics', 'resizable', '0')

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import Metrics
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, NoTransition

from tm_channels import CHANNEL_COLORS, CHANNEL_NAMES, MAX_HISTORY, NUM_CHANNELS
from tm_csv_logger import CsvSampleLogger
from tm_display_mode import is_touch_display_mode
from tm_kivy_hw import KivyHwPoller
from tm_kivy_screens import (
    BG_COLOR,
    ControlSidebar,
    PlotScreen,
    SettingsScreen,
    STATUS_FONT,
    TEXT_COLOR,
)
from tm_settings import DEFAULT_PLOT_WINDOW_KEY, plot_window_seconds


class TempMonitorKivyApp(App):
    title = 'TempMonitor (Kivy)'

    def build(self):
        if is_touch_display_mode():
            Metrics.density = 1.0

        Window.clearcolor = BG_COLOR

        self._histories = {
            name: collections.deque(maxlen=MAX_HISTORY) for name in CHANNEL_NAMES}
        self._active = [True, False, False, False, False, False]
        self._tc_mask = [True, False, False, False]
        self._cjc_on = False
        self._plot_t0 = 0.0
        self._reset_plot_t0 = False
        self._plot_window_key = DEFAULT_PLOT_WINDOW_KEY
        self._logger = CsvSampleLogger()
        self._status_base = ''

        self._hw = KivyHwPoller()
        root = BoxLayout(orientation='horizontal', padding=0, spacing=0)

        self._sidebar = ControlSidebar(self)
        root.add_widget(self._sidebar)

        right = BoxLayout(orientation='vertical', spacing=0)

        status_row = BoxLayout(size_hint_y=None, height=32, spacing=4, padding=(4, 2))
        self._status_label = Label(
            text='Starte Messung …',
            size_hint_x=1,
            font_size=STATUS_FONT,
            halign='left',
            valign='middle',
            color=TEXT_COLOR,
        )
        self._status_label.bind(size=self._wrap_status)
        status_row.add_widget(self._status_label)
        exit_btn = Button(
            text='Beenden',
            size_hint_x=None,
            width=90,
            font_size='13sp',
            background_normal='',
            background_color=(0.55, 0.18, 0.18, 1),
        )
        exit_btn.bind(on_release=lambda *_: self.request_exit())
        status_row.add_widget(exit_btn)
        right.add_widget(status_row)

        self._screen_mgr = ScreenManager(transition=NoTransition(), size_hint_y=1)
        self._plot_screen = PlotScreen(name='plot')
        self._settings_screen = SettingsScreen(self, name='settings')
        for scr in (self._plot_screen, self._settings_screen):
            self._screen_mgr.add_widget(scr)
        right.add_widget(self._screen_mgr)

        root.add_widget(right)

        self._push_channel_config()
        self._hw.start()
        Clock.schedule_interval(self._poll_hw, 0.05)
        return root

    def request_exit(self):
        self.stop()

    @property
    def logger(self):
        return self._logger

    @property
    def plot_window_key(self):
        return self._plot_window_key

    def _wrap_status(self, instance, value):
        instance.text_size = (value[0] - 4, None)

    def _poll_hw(self, _dt):
        """One sample per tick — avoids burst plotting when UI was busy."""
        item = self._hw.poll_one()
        if item is None:
            return
        kind, *payload = item
        if kind == 'sample':
            packet, status = payload
            self._handle_sample(packet)
            self._set_status_base(status)
        elif kind == 'error':
            self._show_error(payload[0])

    def switch_view(self, view_name):
        if self._screen_mgr.current != view_name:
            self._screen_mgr.current = view_name
        self._sidebar.select_view(view_name)

    def channel_tc_mask(self):
        return list(self._tc_mask)

    def channel_cjc_enabled(self):
        return self._cjc_on

    def set_plot_window_key(self, key):
        self._plot_window_key = key
        self._refresh_plot()

    def set_missing_key(self, key):
        self._logger.set_missing_key(key)

    def _active_mask(self):
        mask = list(self._tc_mask)
        mask.append(self._cjc_on)
        mask.append(self._cjc_on)
        return mask

    def _any_sensor_active(self):
        return any(self._tc_mask) or self._cjc_on

    def _other_channels_active(self, skip_tc_idx=None, skip_cjc=False):
        for i in range(4):
            if skip_tc_idx is not None and i == skip_tc_idx:
                continue
            if self._tc_mask[i]:
                return True
        if not skip_cjc and self._cjc_on:
            return True
        return False

    def _maybe_reset_plot_time(self, checked, skip_tc_idx=None, skip_cjc=False):
        if checked and not self._other_channels_active(skip_tc_idx, skip_cjc):
            self._reset_plot_t0 = True

    def _clear_trace(self, name):
        self._histories[name].clear()

    def on_tc_toggle(self, idx, checked):
        self._tc_mask[idx] = checked
        if checked:
            self._clear_trace(CHANNEL_NAMES[idx])
            self._maybe_reset_plot_time(checked, skip_tc_idx=idx)
        self._push_channel_config()

    def on_cjc_toggle(self, checked):
        self._cjc_on = checked
        if checked:
            self._clear_trace('U1 CJC')
            self._clear_trace('U2 CJC')
            self._maybe_reset_plot_time(checked, skip_cjc=True)
        self._push_channel_config()

    def _stop_logging(self):
        self._logger.stop()
        self._sidebar.set_logging_off()
        self._update_status_display()

    def on_logging_toggle(self, checked):
        if checked:
            if not self._any_sensor_active():
                self._sidebar.set_logging_off()
                return
            self._logger.start()
            self._sidebar.set_logging_on()
        else:
            self._stop_logging()
        self._update_status_display()

    def _push_channel_config(self):
        self._active = self._active_mask()
        self._hw.set_active_channels(self._tc_mask, self._cjc_on)
        self._refresh_plot()
        if self._logger.enabled and not self._any_sensor_active():
            self._stop_logging()

    def _filter_for_window(self, visible):
        window_sec = plot_window_seconds(self._plot_window_key)
        if window_sec is None or window_sec <= 0:
            return visible
        x_max = 0.0
        for points in visible.values():
            for t, _val in points:
                if t > x_max:
                    x_max = t
        x_min = max(0.0, x_max - float(window_sec))
        filtered = {}
        for name, points in visible.items():
            filtered[name] = [(t, v) for t, v in points if t >= x_min]
        return filtered

    def _refresh_plot(self, _dt=None):
        visible = {
            CHANNEL_NAMES[i]: list(self._histories[CHANNEL_NAMES[i]])
            for i in range(NUM_CHANNELS)
            if self._active[i]
        }
        visible = self._filter_for_window(visible)
        if visible:
            self._plot_screen.plot.set_series_snapshot(
                visible, t0=0.0, colors=CHANNEL_COLORS)
        else:
            self._plot_screen.plot.clear_series()

    def _handle_sample(self, packet):
        if not packet:
            return
        if self._reset_plot_t0:
            self._plot_t0 = packet[0][0]
            self._reset_plot_t0 = False
        if self._logger.enabled:
            self._logger.write_packet(packet, self._tc_mask, self._cjc_on)
        for i, (t_sec, temp_c) in enumerate(packet):
            if not self._active[i] or temp_c is None:
                continue
            name = CHANNEL_NAMES[i]
            self._histories[name].append((t_sec - self._plot_t0, temp_c))
        self._refresh_plot()

    def _set_status_base(self, text):
        self._status_base = text
        self._update_status_display()

    def _update_status_display(self):
        text = self._status_base
        if self._logger.enabled and self._logger.path:
            text = text + '   |   Log: {0}'.format(self._logger.path)
        self._status_label.text = text

    def _show_error(self, message):
        self._status_label.text = 'Fehler: {0}'.format(message)

    def on_stop(self):
        self._logger.stop()
        self._hw.stop()


def _acquire_single_instance_lock():
    lock_path = '/tmp/tm_kivy_app.lock'
    lock_fp = open(lock_path, 'w')
    try:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('TempMonitor Kivy laeuft bereits.', file=sys.stderr)
        return None
    lock_fp.write(str(os.getpid()))
    lock_fp.flush()
    return lock_fp


def main():
    os.environ.setdefault('DISPLAY', ':0')
    os.environ.setdefault('KIVY_BCM_DISPMANX_ID', '0')
    if _acquire_single_instance_lock() is None:
        return 0
    return TempMonitorKivyApp().run()


if __name__ == '__main__':
    sys.exit(main())
