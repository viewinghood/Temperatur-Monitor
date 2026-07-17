# -*- coding: utf-8 -*-
"""Display mode and hardware presence (HDMI / 7" DSI touch)."""

import glob
import os
import re
import subprocess

KIVY_DISPLAY_ENV = os.path.expanduser('~/.config/tm_kivy_display.env')
TOUCH_INPUT = '/dev/input/by-path/platform-soc:firmware:touchscreen-event'
BOOT_CONFIG = '/boot/config.txt'
HDMI_ATTACHED_BIT = 0x2


def is_touch_display_mode():
    """True when set_touch_display.sh touch has been applied (needs reboot)."""
    return os.path.isfile(KIVY_DISPLAY_ENV)


def _run_tvservice(args):
    try:
        proc = subprocess.run(
            ['tvservice'] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
            universal_newlines=True,
        )
        return proc.stdout or ''
    except (OSError, subprocess.SubprocessError):
        return ''


def _tvservice_list():
    return _run_tvservice(['-l'])


def _tvservice_status():
    return _run_tvservice(['-s'])


def _parse_hdmi_attached_bit(status_text):
    match = re.search(r'state\s+(0x[0-9a-fA-F]+)', status_text or '')
    if not match:
        return None
    return bool(int(match.group(1), 16) & HDMI_ATTACHED_BIT)


def _hdmi_sysfs_connected():
    for path in glob.glob('/sys/class/drm/card*-HDMI-A-*/status'):
        try:
            with open(path, encoding='utf-8') as handle:
                state = handle.read().strip().lower()
        except OSError:
            continue
        if state == 'connected':
            return True
        if state == 'disconnected':
            return False
    return None


def _boot_config_text():
    try:
        with open(BOOT_CONFIG, encoding='utf-8', errors='ignore') as handle:
            return handle.read()
    except OSError:
        return ''


def _dsi_panel_configured():
    """True when the official DSI panel is configured in /boot/config.txt."""
    cfg = _boot_config_text()
    if not cfg:
        return False
    if 'display_default_lcd=1' in cfg:
        return True
    if re.search(r'^lcd_rotate=', cfg, re.MULTILINE):
        return True
    if re.search(
            r'^dtoverlay=.*(?:dsi|7inch|rpi-display)',
            cfg,
            re.MULTILINE | re.IGNORECASE):
        return True
    return False


def _hdmi_listed_as_attached(list_text):
    if not list_text:
        return False
    return any('type HDMI' in line for line in list_text.splitlines())


def hdmi_display_attached():
    """True when an HDMI monitor is hot-plugged (powered off is still OK)."""
    sysfs = _hdmi_sysfs_connected()
    if sysfs is not None:
        return sysfs

    status = _tvservice_status()
    listed = _tvservice_list()
    attached_bit = _parse_hdmi_attached_bit(status)

    # Active HDMI output: hotplug bit is authoritative (cable out -> grey out).
    if attached_bit is not None and (
            'HDMI' in status or 'DVI' in status or 'TV is off' in status):
        return attached_bit

    # Touch/DSI is primary: HDMI only counts if firmware lists it attached.
    if 'Main LCD' in listed or 'type Main LCD' in listed:
        return _hdmi_listed_as_attached(listed)

    if attached_bit is not None:
        return attached_bit
    return False


def dsi_touch_attached():
    """True when the 7" DSI panel is present (even if ignore_lcd=1 in HDMI mode)."""
    if os.path.exists(TOUCH_INPUT):
        return True
    listed = _tvservice_list()
    if 'Main LCD' in listed or 'type Main LCD' in listed:
        return True
    return _dsi_panel_configured()


def display_switch_available():
    """Which display switch targets are physically available."""
    return {
        'hdmi': hdmi_display_attached(),
        'touch': dsi_touch_attached(),
    }


def display_switch_target(on_touch_mode):
    """UI state for the display switch button in settings."""
    avail = display_switch_available()
    if on_touch_mode:
        enabled = avail['hdmi']
        label = 'HDMI (Eizo)'
        if not enabled:
            label = 'HDMI (Eizo) — nicht angeschlossen'
    else:
        enabled = avail['touch']
        label = '7" Touch (DSI)'
        if not enabled:
            label = '7" Touch — nicht angeschlossen'
    return {
        'label': label,
        'enabled': enabled,
        'hdmi': avail['hdmi'],
        'touch': avail['touch'],
    }
