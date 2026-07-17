# -*- coding: utf-8 -*-
"""Apply display mode switch (touch/HDMI) and reboot."""

import os
import subprocess
import threading

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SET_DISPLAY_SH = os.path.join(SCRIPT_DIR, 'set_touch_display.sh')


def _run_switch(mode):
    subprocess.Popen(
        ['sudo', 'bash', SET_DISPLAY_SH, mode],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    threading.Timer(1.5, _reboot).start()


def _reboot():
    subprocess.Popen(
        ['sudo', 'reboot'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def apply_hdmi_switch_and_reboot():
    """Switch to HDMI (Eizo) and reboot."""
    _run_switch('hdmi')


def apply_touch_switch_and_reboot():
    """Switch to 7\" DSI touch display and reboot."""
    _run_switch('touch')
