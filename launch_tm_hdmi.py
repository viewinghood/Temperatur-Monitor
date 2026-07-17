#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Desktop launcher — HDMI PyQt app (single-click .desktop, no shell in Exec)."""

import os
import subprocess
import sys

DEV = os.path.dirname(os.path.abspath(__file__))
os.chdir(DEV)
os.environ.setdefault('DISPLAY', ':0')
os.environ.setdefault('XAUTHORITY', os.path.expanduser('~/.Xauthority'))

APP = 'tm_pyqt_plot_app.py'
LOCK = '/tmp/tm_pyqt_plot_app.lock'


def _running():
    r = subprocess.run(
        ['pgrep', '-f', 'python3 {0}'.format(APP)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def main():
    if _running():
        return 0
    subprocess.run(
        ['pkill', '-f', 'python3 tm_kivy_app.py'],
        stderr=subprocess.DEVNULL)
    os.execv(sys.executable, [sys.executable, os.path.join(DEV, APP)] + sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main() or 0)
