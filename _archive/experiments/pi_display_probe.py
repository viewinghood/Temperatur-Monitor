#!/usr/bin/env python3
"""One-shot probe for Pi display detection (deploy/run on Pi)."""
import glob
import os
import re
import subprocess

BOOT = '/boot/config.txt'
TOUCH = '/dev/input/by-path/platform-soc:firmware:touchscreen-event'


def run(cmd):
    try:
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=3, check=False, universal_newlines=True)
        return p.stdout or ''
    except (OSError, subprocess.SubprocessError):
        return ''


def main():
    print('=== tvservice -l ===')
    listed = run(['tvservice', '-l']).strip()
    print(listed)
    print('=== tvservice -s ===')
    status = run(['tvservice', '-s']).strip()
    print(status)
    m = re.search(r'state\s+(0x[0-9a-fA-F]+)', status)
    if m:
        v = int(m.group(1), 16)
        print('HDMI_ATTACHED bit:', bool(v & 2), 'state=', hex(v))
    print('=== tvservice -n ===')
    print(run(['tvservice', '-n']).strip())
    print('=== touch input ===', os.path.exists(TOUCH))
    try:
        cfg = open(BOOT, encoding='utf-8', errors='ignore').read()
    except OSError:
        cfg = ''
    print('lcd_rotate', bool(re.search(r'^lcd_rotate=', cfg, re.M)))
    print('display_default_lcd', 'display_default_lcd=1' in cfg)
    print('ignore_lcd', 'ignore_lcd=1' in cfg)
    for p in glob.glob('/sys/class/drm/card*-HDMI-A-*/status'):
        print('sysfs', p, open(p, encoding='utf-8').read().strip())


if __name__ == '__main__':
    main()
