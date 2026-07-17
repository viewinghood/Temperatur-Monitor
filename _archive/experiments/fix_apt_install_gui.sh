#!/bin/bash
set -e
# Fix apt mirror redirect to broken halifax — use IPv4 + official mirror
sudo rm -f /etc/apt/apt.conf.d/99force-ipv4
printf '%s\n' 'Acquire::ForceIPv4 "true";' | sudo tee /etc/apt/apt.conf.d/99force-ipv4 >/dev/null

sudo tee /etc/apt/sources.list >/dev/null << 'EOF'
deb http://raspbian.raspberrypi.org/raspbian/ bullseye main contrib non-free rpi
#deb-src http://raspbian.raspberrypi.org/raspbian/ bullseye main contrib non-free rpi
EOF

sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/*
sudo apt-get update

sudo apt-get install -y \
    python3-pip python3-dev \
    python3-kivy python3-pyqt5 python3-pyqtgraph python3-pyqt5.qtsvg \
    libmtdev1 libgl1-mesa-dri

python3 << 'PY'
import kivy, pyqtgraph, numpy
from PyQt5 import QtWidgets
print('kivy', kivy.__version__)
print('pyqtgraph', pyqtgraph.__version__)
print('numpy', numpy.__version__)
print('ALL_OK')
PY

date > ~/py/TempMonitor/dev/READY_bullseye_gui.txt
echo "apt python3.9 stack" >> ~/py/TempMonitor/dev/READY_bullseye_gui.txt
echo DONE
