# -*- coding: utf-8 -*-
"""
Touch-friendly launcher: switch from 7" DSI back to HDMI (Eizo) and reboot.

Run: ~/py/TempMonitor/dev/start_tm_switch_hdmi.sh
Desktop: SwitchToHDMI.desktop
"""

import os
import sys

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from tm_display_mode import is_touch_display_mode
from tm_display_switch import apply_hdmi_switch_and_reboot

BG_COLOR = (0.10, 0.10, 0.18, 1)
TEXT_COLOR = (0.92, 0.92, 0.92, 1)
MUTED_COLOR = (0.65, 0.65, 0.70, 1)


class SwitchHdmiApp(App):
    title = 'HDMI umschalten'

    def build(self):
        Window.clearcolor = BG_COLOR
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))

        root.add_widget(Label(
            text='Display-Umschaltung',
            size_hint_y=None,
            height=dp(48),
            font_size='22sp',
            color=TEXT_COLOR,
        ))

        if not is_touch_display_mode():
            root.add_widget(Label(
                text='Bereits HDMI-Modus (Eizo).\nKein Umschalten noetig.',
                font_size='18sp',
                color=MUTED_COLOR,
                halign='center',
            ))
            close = Button(
                text='Schliessen',
                size_hint_y=None,
                height=dp(72),
                font_size='18sp',
            )
            close.bind(on_press=lambda *_: self.stop())
            root.add_widget(close)
            return root

        hint = Label(
            text='7"-Touch-Display aktiv.\nZurueck auf den Eizo-Monitor (HDMI)?',
            font_size='17sp',
            color=MUTED_COLOR,
            halign='center',
        )
        hint.bind(size=lambda inst, val: setattr(
            inst, 'text_size', (val[0], None)))
        root.add_widget(hint)

        btn = Button(
            text='HDMI (Eizo)\nUmschalten + Neustart',
            font_size='20sp',
            size_hint_y=1,
        )
        btn.bind(on_press=self._confirm)
        root.add_widget(btn)
        return root

    def _confirm(self, _btn):
        content = BoxLayout(
            orientation='vertical', spacing=dp(10), padding=dp(12))
        msg = Label(
            text=(
                'Display auf HDMI (Eizo) umstellen?\n\n'
                'Der Raspberry Pi startet danach neu.'),
            font_size='18sp',
            halign='center',
            color=TEXT_COLOR,
        )
        msg.bind(size=lambda inst, val: setattr(
            inst, 'text_size', (val[0], None)))
        content.add_widget(msg)

        row = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(8))
        popup = Popup(
            title='Bestaetigen',
            content=content,
            size_hint=(0.92, 0.45),
            separator_color=BG_COLOR,
        )
        cancel = Button(text='Abbrechen', font_size='18sp')
        ok = Button(text='Ja, umschalten', font_size='18sp')
        row.add_widget(cancel)
        row.add_widget(ok)
        content.add_widget(row)
        cancel.bind(on_press=popup.dismiss)
        ok.bind(on_press=lambda *_: (popup.dismiss(), self._apply()))
        popup.open()

    def _apply(self):
        apply_hdmi_switch_and_reboot()


def main():
    os.environ.setdefault('DISPLAY', ':0')
    if is_touch_display_mode():
        os.environ.setdefault('KIVY_BCM_DISPMANX_ID', '0')
    return SwitchHdmiApp().run()


if __name__ == '__main__':
    sys.exit(main())
