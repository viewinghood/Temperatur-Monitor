#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Desktop launcher — 7\" Touch PyQt app (single-click .desktop, no shell in Exec)."""

import os
import subprocess
import sys

DEV = os.path.dirname(os.path.abspath(__file__))
os.chdir(DEV)
os.environ.setdefault('DISPLAY', ':0')
os.environ.setdefault('XAUTHORITY', os.path.expanduser('~/.Xauthority'))

APP = 'tm_pyqt_touch_app.py'
LOG = os.path.join(DEV, 'tm_pyqt_touch_gui.log')
ENV_FILE = os.path.expanduser('~/.config/tm_kivy_display.env')


def _load_display_env():
    if not os.path.isfile(ENV_FILE):
        return
    with open(ENV_FILE, encoding='utf-8') as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[7:]
            key, _, val = line.partition('=')
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), val)


def _running():
    r = subprocess.run(
        ['pgrep', '-f', 'python3 {0}'.format(APP)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def main():
    _load_display_env()
    if _running():
        return 0
    for pat in ('python3 tm_kivy_app.py', 'python3 tm_pyqt_plot_app.py'):
        subprocess.run(['pkill', '-f', pat], stderr=subprocess.DEVNULL)
    log_fp = open(LOG, 'a', encoding='utf-8')
    os.dup2(log_fp.fileno(), 1)
    os.dup2(log_fp.fileno(), 2)
    os.execv(sys.executable, [sys.executable, os.path.join(DEV, APP)] + sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main() or 0)
