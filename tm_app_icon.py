# -*- coding: utf-8 -*-
"""Shared window / taskbar icon for TempMonitor PyQt apps."""

import os

from PyQt5.QtGui import QIcon

DEV_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(DEV_DIR, 'icons', 'tempmonitor-48.png')
FALLBACK_ICON = '/usr/share/icons/PiXflat/48x48/apps/utilities-system-monitor.png'


def icon_path():
    if os.path.isfile(ICON_PATH):
        return ICON_PATH
    if os.path.isfile(FALLBACK_ICON):
        return FALLBACK_ICON
    return None


def apply_app_icon(app, window=None, desktop_file=None):
    path = icon_path()
    if path:
        icon = QIcon(path)
        app.setWindowIcon(icon)
        if window is not None:
            window.setWindowIcon(icon)
    if desktop_file and hasattr(app, 'setDesktopFileName'):
        app.setDesktopFileName(desktop_file)
