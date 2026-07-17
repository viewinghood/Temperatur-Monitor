#!/bin/bash
# PyQt5 only (NO PySide) — idempotent, resume-safe
LOG="$HOME/py/TempMonitor/dev/install_pyqt5.log"
PREFIX="$HOME/local/python311"
OPENSSL="$HOME/local/openssl111/lib"
QT515="$HOME/local/qt515"
QT_SRC=/tmp/qtbase-everywhere-src-5.15.16
QT_TAR=/tmp/qtbase-everywhere-src-5.15.16.tar.xz
QT_URL="https://mirrors.ukfast.co.uk/sites/qt.io/archive/qt/5.15/5.15.16/submodules/qtbase-everywhere-opensource-src-5.15.16.tar.xz"
LOCK="$HOME/py/TempMonitor/dev/install_pyqt5.lock"

LOCK="$HOME/py/TempMonitor/dev/install.lock"
exec 9>"$LOCK"
flock -n 9 || { echo "Another install_pyqt5 running — exit"; exit 0; }

exec >> "$LOG" 2>&1
echo "=== $(date) install_pyqt5.sh pid=$$ ==="

export PATH="$PREFIX/bin:$PATH"
export LD_LIBRARY_PATH="$OPENSSL:$LD_LIBRARY_PATH"

try_pyqt5() {
    local q="$1"
    echo "Trying PyQt5 with QMAKE=$q"
    export PATH="${q%/*}:$PATH"
    export QMAKE="$q"
    export QT_SELECT=5
    # License + build (pip 26 on Stretch)
    pip install --default-timeout=300 --retries 5 --no-cache-dir --no-build-isolation PyQt5 \
        || pip install --default-timeout=300 --retries 5 --no-cache-dir --no-build-isolation \
            --config-settings confirm_license=true PyQt5 \
        || return 1
    return 0
}

verify_all() {
    python3.11 -c "import PyQt5.QtWidgets; import pyqtgraph; import kivy; print('ALL OK')" \
        && echo "=== $(date) install_pyqt5 DONE ===" \
        && date > "$HOME/py/TempMonitor/dev/READY_py311_gui.txt"
}

# Already complete?
if [ -f "$HOME/py/TempMonitor/dev/READY_py311_gui.txt" ]; then
    echo "Already READY — skip"
    exit 0
fi
if python3.11 -c "import PyQt5.QtWidgets" 2>/dev/null; then
    verify_all && exit 0
fi

# Qt 5.15 ready → only PyQt5
if [ -x "$QT515/bin/qmake" ]; then
    pip install --default-timeout=180 --retries 3 sip pyqt-builder PyQt5-sip 2>/dev/null || true
    try_pyqt5 "$QT515/bin/qmake" && verify_all && exit 0
    echo "PyQt5 failed with existing Qt 5.15"
    exit 1
fi

# Resume or fresh Qt build
pip install --default-timeout=180 --retries 3 sip pyqt-builder PyQt5-sip 2>/dev/null || true

if [ ! -f "$QT_TAR" ] || [ "$(stat -c%s "$QT_TAR" 2>/dev/null || echo 0)" -lt 40000000 ]; then
    echo "Downloading qtbase..."
    wget -c -O "$QT_TAR" "$QT_URL" || exit 1
fi

if [ ! -d "$QT_SRC" ]; then
    echo "Extracting qtbase..."
    tar xf "$QT_TAR" -C /tmp
fi

cd "$QT_SRC" || exit 1

if [ ! -f Makefile ]; then
    echo "Configuring Qt 5.15.16..."
    ./configure -prefix "$QT515" -release -opensource -confirm-license \
        -nomake examples -nomake tests -nomake tools \
        -no-opengl -no-gtk -no-openssl -qt-zlib -qt-libpng -qt-libjpeg \
        || exit 1
fi

echo "Building Qt (make -j1, resume OK)..."
make -j1 || exit 1
make install || exit 1
echo "Qt installed: $($QT515/bin/qmake -version | head -1)"

try_pyqt5 "$QT515/bin/qmake" || exit 1
verify_all
