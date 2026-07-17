# -*- coding: utf-8 -*-
"""Kivy screens — left sidebar, plot, settings (800x448 touch layout)."""

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from pg_plot_kivy_widget import PyQtGraphPlotWidget
from tm_channels import CHANNEL_NAMES
from tm_display_mode import is_touch_display_mode
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

SIDEBAR_WIDTH = 108
BTN_FONT = '13sp'
STATUS_FONT = '13sp'
SECTION_FONT = '15sp'
BG_COLOR = (0.10, 0.10, 0.18, 1)
TEXT_COLOR = (0.92, 0.92, 0.92, 1)
MUTED_COLOR = (0.65, 0.65, 0.70, 1)
SPINNER_H = 42
BTN_OFF = (0.28, 0.28, 0.36, 1)
BTN_ON = (0.10, 0.45, 0.82, 1)
BTN_LOG_ON = (0.263, 0.627, 0.278, 1)
BTN_NAV = (0.22, 0.35, 0.55, 1)
BTN_EXIT = (0.55, 0.18, 0.18, 1)


class SideButton(Button):
    """Touch-friendly sidebar button — grab on press, fire on release in bounds."""

    def __init__(self, callback=None, toggle=False, active=False,
                 color_on=None, color_off=None, **kwargs):
        self._callback = callback
        self._toggle = toggle
        self._active = active
        self._color_on = color_on or BTN_ON
        self._color_off = color_off or BTN_OFF
        self._armed = False
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        kwargs.setdefault('always_release', True)
        super(SideButton, self).__init__(**kwargs)
        self._sync_color()

    def on_touch_down(self, touch):
        if self.disabled or not self.collide_point(*touch.pos):
            return super(SideButton, self).on_touch_down(touch)
        touch.grab(self)
        self._armed = True
        self._sync_color(pressed=True)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            return True
        return super(SideButton, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super(SideButton, self).on_touch_up(touch)
        touch.ungrab(self)
        if self._armed and self.collide_point(*touch.pos):
            self._handle_click()
        self._armed = False
        self._sync_color(pressed=False)
        return True

    def on_release(self):
        pass

    def _handle_click(self):
        if self._toggle:
            new_active = not self._active
            self._active = new_active
            self._sync_color()
            if self._callback:
                self._callback(new_active)
        elif self._callback:
            self._callback()

    def set_active(self, active):
        self._active = bool(active)
        self._sync_color()

    def _sync_color(self, pressed=False):
        if self._toggle:
            base = self._color_on if self._active else self._color_off
        else:
            base = BTN_NAV
        if pressed:
            self.background_color = tuple(max(0.0, c - 0.10) for c in base)
        else:
            self.background_color = base


class HamburgerSideButton(SideButton):
    """Settings — three bars drawn in canvas (no Unicode font needed)."""

    def __init__(self, **kwargs):
        kwargs.setdefault('text', '')
        super(HamburgerSideButton, self).__init__(**kwargs)
        self.bind(pos=self._draw_icon, size=self._draw_icon)
        Clock.schedule_once(lambda _dt: self._draw_icon(), 0)

    def _draw_icon(self, *_args):
        self.canvas.after.clear()
        if self.width < 4 or self.height < 4:
            return
        pad_x = self.width * 0.20
        bar_w = self.width - 2 * pad_x
        bar_h = max(2.0, self.height * 0.05)
        gap = self.height * 0.14
        cy = self.y + self.height * 0.5
        with self.canvas.after:
            Color(0.92, 0.92, 0.92, 1)
            for i in (-1, 0, 1):
                y = cy + i * gap - bar_h * 0.5
                Rectangle(pos=(self.x + pad_x, y), size=(bar_w, bar_h))


class ControlSidebar(BoxLayout):
    """Left column — 8 equal rows."""

    def __init__(self, app_ref, **kwargs):
        super(ControlSidebar, self).__init__(**kwargs)
        self.app_ref = app_ref
        self.orientation = 'vertical'
        self.size_hint_x = None
        self.width = SIDEBAR_WIDTH
        self.spacing = 0
        self.padding = [0, 2]

        grid = GridLayout(cols=1, rows=8, spacing=1, size_hint=(1, 1))

        self._tc_buttons = []
        for i, name in enumerate(CHANNEL_NAMES[:4]):
            btn = SideButton(
                text=name,
                toggle=True,
                active=(i == 0),
                font_size=BTN_FONT,
                size_hint_y=1,
                callback=lambda on, idx=i: app_ref.on_tc_toggle(idx, on),
            )
            self._tc_buttons.append(btn)
            grid.add_widget(btn)

        self._cjc_btn = SideButton(
            text='Chip CJC',
            toggle=True,
            active=False,
            font_size=BTN_FONT,
            size_hint_y=1,
            callback=app_ref.on_cjc_toggle,
        )
        grid.add_widget(self._cjc_btn)

        self._log_btn = SideButton(
            text='Logging',
            toggle=True,
            active=False,
            font_size=BTN_FONT,
            size_hint_y=1,
            color_on=BTN_LOG_ON,
            callback=app_ref.on_logging_toggle,
        )
        grid.add_widget(self._log_btn)

        self._plot_btn = SideButton(
            text='Plot',
            font_size=BTN_FONT,
            size_hint_y=1,
            callback=lambda: app_ref.switch_view('plot'),
        )
        grid.add_widget(self._plot_btn)

        self._setup_btn = HamburgerSideButton(
            size_hint_y=1,
            callback=lambda: app_ref.switch_view('settings'),
        )
        grid.add_widget(self._setup_btn)

        self.add_widget(grid)

    def select_view(self, view_name):
        self._plot_btn.background_color = (
            BTN_ON if view_name == 'plot' else BTN_NAV)
        self._setup_btn.background_color = (
            BTN_ON if view_name == 'settings' else BTN_NAV)

    def set_logging_off(self):
        self._log_btn.set_active(False)

    def set_logging_on(self):
        self._log_btn.set_active(True)


class PlotScreen(Screen):
    def __init__(self, **kwargs):
        super(PlotScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=0, padding=0)
        self.plot = PyQtGraphPlotWidget()
        layout.add_widget(self.plot)
        self.add_widget(layout)


class SettingsScreen(Screen):
    def __init__(self, app_ref, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.app_ref = app_ref

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        root = BoxLayout(
            orientation='vertical',
            padding=dp(6),
            spacing=dp(6),
            size_hint_y=None,
        )
        root.bind(minimum_height=root.setter('height'))

        root.add_widget(Label(
            text='Einstellungen',
            size_hint_y=None,
            height=dp(28),
            font_size=SECTION_FONT,
            color=TEXT_COLOR,
            halign='left',
        ))

        info = Label(
            text='System: {0}\nLog: {1}'.format(
                os_display_name(), log_dir_for_display()),
            size_hint_y=None,
            font_size='12sp',
            color=MUTED_COLOR,
            halign='left',
            valign='top',
        )
        info.bind(
            texture_size=lambda inst, val: setattr(inst, 'height', val[1]),
            size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)),
        )
        root.add_widget(info)

        root.add_widget(self._section('Plot-Zeitfenster'))
        self._window_spinner = Spinner(
            text=self._label_for_key(
                app_ref.plot_window_key, PLOT_WINDOW_LABELS),
            values=[label for _k, label in PLOT_WINDOW_LABELS],
            size_hint_y=None,
            height=SPINNER_H,
            font_size=BTN_FONT,
        )
        self._window_spinner.bind(text=self._on_window_pick)
        root.add_widget(self._window_spinner)

        root.add_widget(self._section('Kein Messwert (CSV)'))
        self._missing_spinner = Spinner(
            text=self._label_for_key(
                app_ref.logger.missing_key, MISSING_LABELS),
            values=[label for _k, label in MISSING_LABELS],
            size_hint_y=None,
            height=SPINNER_H,
            font_size=BTN_FONT,
        )
        self._missing_spinner.bind(text=self._on_missing_pick)
        root.add_widget(self._missing_spinner)

        if is_touch_display_mode():
            root.add_widget(self._section('Display'))
            hdmi_btn = Button(
                text='HDMI (Eizo)',
                size_hint_y=None,
                height=SPINNER_H,
                font_size=BTN_FONT,
            )
            hdmi_btn.bind(on_release=self._confirm_hdmi)
            root.add_widget(hdmi_btn)
        else:
            root.add_widget(self._section('Display'))
            touch_btn = Button(
                text='7" Touch',
                size_hint_y=None,
                height=SPINNER_H,
                font_size=BTN_FONT,
            )
            touch_btn.bind(on_release=self._confirm_touch)
            root.add_widget(touch_btn)

        exit_btn = Button(
            text='App beenden',
            size_hint_y=None,
            height=SPINNER_H,
            font_size=BTN_FONT,
            background_normal='',
            background_color=BTN_EXIT,
        )
        exit_btn.bind(on_release=lambda *_: app_ref.request_exit())
        root.add_widget(exit_btn)

        scroll.add_widget(root)
        self.add_widget(scroll)

    def _section(self, title):
        return Label(
            text=title,
            size_hint_y=None,
            height=dp(26),
            font_size=SECTION_FONT,
            color=TEXT_COLOR,
            halign='left',
        )

    def _label_for_key(self, key, options):
        for k, label in options:
            if k == key:
                return label
        return options[0][1]

    def _key_for_label(self, label, options):
        for k, lbl in options:
            if lbl == label:
                return k
        return options[0][0]

    def _on_window_pick(self, spinner, text):
        key = self._key_for_label(text, PLOT_WINDOW_LABELS)
        self.app_ref.set_plot_window_key(key)

    def _on_missing_pick(self, spinner, text):
        key = self._key_for_label(text, MISSING_LABELS)
        self.app_ref.set_missing_key(key)

    def _confirm_hdmi(self, _btn):
        self._confirm_switch(
            'Display auf HDMI (Eizo) umstellen?\n\n'
            'Der Raspberry Pi startet danach neu.',
            apply_hdmi_switch_and_reboot)

    def _confirm_touch(self, _btn):
        self._confirm_switch(
            'Display auf 7"-Touch (DSI) umstellen?\n\n'
            'Der Raspberry Pi startet danach neu.',
            apply_touch_switch_and_reboot)

    def _confirm_switch(self, message, apply_fn):
        content = BoxLayout(
            orientation='vertical', spacing=dp(8), padding=dp(10))
        msg = Label(
            text=message,
            font_size='15sp',
            halign='center',
            color=TEXT_COLOR,
        )
        msg.bind(size=lambda inst, val: setattr(
            inst, 'text_size', (val[0], None)))
        content.add_widget(msg)
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        popup = Popup(
            title='Bestaetigen',
            content=content,
            size_hint=(0.85, 0.38),
            separator_color=BG_COLOR,
        )
        cancel = Button(text='Nein', font_size=BTN_FONT)
        ok = Button(text='Ja', font_size=BTN_FONT)
        row.add_widget(cancel)
        row.add_widget(ok)
        content.add_widget(row)
        cancel.bind(on_release=popup.dismiss)
        ok.bind(on_release=lambda *_: (popup.dismiss(), apply_fn()))
        popup.open()
