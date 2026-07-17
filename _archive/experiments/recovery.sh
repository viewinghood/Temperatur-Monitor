#!/bin/bash
set -e
# PyQt5: wget tarball + project.py (no pip metadata - saves RAM on Pi 3)
DEV="$HOME/py/TempMonitor/dev"
LOG="$DEV/recovery.log"
PREFIX="$HOME/local/python311"
OPENSSL="$HOME/local/openssl111/lib"
QT515="$HOME/local/qt515"
LOCK="$DEV/install.lock"
PYQT_TAR=/tmp/PyQt5-5.15.11.tar.gz
PYQT_SRC=/tmp/PyQt5-5.15.11

find_pyqt_tarball() {
    for f in /tmp/pip-unpack-*/PyQt5-5.15.11.tar.gz \
             /tmp/pyqtdl/PyQt5-5.15.11.tar.gz \
             "$PYQT_TAR"; do
        if [ -f "$f" ] && [ "$(stat -c%s "$f" 2>/dev/null || echo 0)" -gt 1000000 ]; then
            echo "$f"
            return 0
        fi
    done
    return 1
}

export PATH="$PREFIX/bin:$QT515/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="$OPENSSL:$LD_LIBRARY_PATH"
export QMAKE="$QT515/bin/qmake"

exec >> "$LOG" 2>&1
echo "=== $(date) recovery.sh (wget+project.py) ==="

pkill -f night_monitor.sh 2>/dev/null || true

# Extra swap for compile (Pi 3 has 926 MB RAM)
if ! /sbin/swapon --show | grep -q /swapfile311; then
    if [ ! -f /swapfile311 ]; then
        sudo dd if=/dev/zero of=/swapfile311 bs=1M count=1024 status=none
        sudo chmod 600 /swapfile311
        sudo /sbin/mkswap /swapfile311
    fi
    sudo /sbin/swapon /swapfile311 2>/dev/null || true
fi
free -m | grep -E 'Mem|Swap'

exec 9>"$LOCK"
flock -n 9 || { echo "lock held"; exit 1; }

if python3.11 -c "import PyQt5.QtWidgets" 2>/dev/null; then
    date > "$DEV/READY_py311_gui.txt"
    echo "$(date '+%Y-%m-%d %H:%M:%S') READY" > "$DEV/BUILD_STATUS.txt"
    exit 0
fi

[ -x "$QMAKE" ] || { echo "FATAL: qmake missing"; exit 1; }

if [ ! -f "$PYQT_TAR" ] || [ "$(stat -c%s "$PYQT_TAR" 2>/dev/null || echo 0)" -lt 1000000 ]; then
    SRC_TAR=$(find_pyqt_tarball) || { echo "FATAL: PyQt5 tarball not found"; exit 1; }
    echo "Using tarball: $SRC_TAR"
    cp "$SRC_TAR" "$PYQT_TAR"
fi

if [ ! -d "$PYQT_SRC" ]; then
    echo "Extracting..."
    tar xzf "$PYQT_TAR" -C /tmp
fi

cd "$PYQT_SRC" || exit 1
echo "Building PyQt5 (sip-build)..."
sip-build --confirm-license
sip-install
python3.11 -c "import PyQt5.QtWidgets; import pyqtgraph; import kivy; print('ALL OK')"
date > "$DEV/READY_py311_gui.txt"
echo "$(date '+%Y-%m-%d %H:%M:%S') READY" > "$DEV/BUILD_STATUS.txt"
echo "=== DONE ==="