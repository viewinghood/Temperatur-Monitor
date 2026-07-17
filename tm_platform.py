# -*- coding: utf-8 -*-
"""Platform detection and cross-OS paths for TempMonitor."""

import os
import platform

LOG_DIR_NAME = 'tm_log'


def detect_os_family():
    """
    Return 'windows', 'linux', or 'macos'.
    Linux includes Raspberry Pi OS; macOS includes iMac.
    """
    name = platform.system()
    if name == 'Windows':
        return 'windows'
    if name == 'Darwin':
        return 'macos'
    if name == 'Linux':
        return 'linux'
    return name.lower()


def os_display_name():
    family = detect_os_family()
    labels = {
        'windows': 'Windows',
        'linux': 'Linux',
        'macos': 'macOS (Apple)',
    }
    return labels.get(family, platform.system())


def default_log_dir():
    """
    Log directory in the user home folder:
      Linux / Pi / macOS: ~/tm_log
      Windows:            C:\\Users\\<Benutzer>\\tm_log
    """
    return os.path.join(os.path.expanduser('~'), LOG_DIR_NAME)


def log_dir_for_display():
    """Human-readable path for UI (uses ~ on Unix)."""
    family = detect_os_family()
    home = os.path.expanduser('~')
    if family in ('linux', 'macos'):
        return '~/{}'.format(LOG_DIR_NAME)
    return os.path.join(home, LOG_DIR_NAME)
