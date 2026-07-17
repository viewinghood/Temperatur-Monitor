#!/bin/bash
# Retry GUI stack install — fix apt mirror, install Kivy/PyQt5/pyqtgraph
set -e
LOG="$HOME/py/TempMonitor/dev/install_bullseye_gui.log"
DEV="$HOME/py/TempMonitor/dev"
exec >> "$LOG" 2>&1

echo "=== $(date) install_bullseye_gui.sh RETRY pid=$$ ==="
export DEBIAN_FRONTEND=noninteractive

# Prefer official Raspberry Pi mirror (avoid broken third-party mirrors)
if grep -q halifax /etc/apt/sources.list 2>/dev/null; then
    sudo sed -i 's|http://ftp.halifax.rwth-aachen.de/raspbian/raspbian|http://raspbian.raspberrypi.org/raspbian|g' /etc/apt/sources.list
    echo "Fixed apt mirror in sources.list"
fi

echo "--- apt update ---"
sudo apt-get update -qq

echo "--- apt install (retry) ---"
sudo apt-get install -y --fix-missing \
    python3-kivy python3-pyqt5 python3-pyqt5.qtsvg python3-pyqt5.qtopengl \
    python3-pyqtgraph python3-numpy python3-spidev \
    libgl1-mesa-dri libgles2-mesa libegl1-mesa libmtdev1 \
    2>&1 | tail -25

echo "--- import test ---"
python3 << 'PYEOF'
import kivy, pyqtgraph, numpy
from PyQt5 import QtWidgets
print('kivy', kivy.__version__)
print('pyqtgraph', pyqtgraph.__version__)
print('numpy', numpy.__version__)
print('PyQt5 OK')
print('ALL_IMPORTS_OK')
PYEOF

echo "--- SPI test ---"
cd "$DEV" && python3 spi_adc_tm_try4.py --seconds 2 --sensor 1 | tail -3

date > "$DEV/READY_bullseye_gui.txt"
echo "python3.9 apt stack OK" >> "$DEV/READY_bullseye_gui.txt"
echo "=== $(date) RETRY DONE ==="
