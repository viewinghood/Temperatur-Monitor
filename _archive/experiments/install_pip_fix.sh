#!/bin/bash
# TempMonitor — pip fix (PyQt5 only, NO PySide)
# Run after Python 3.11.11 is installed in ~/local/python311
# Log: ~/py/TempMonitor/dev/install_pip_fix.log

LOG="$HOME/py/TempMonitor/dev/install_pip_fix.log"
PREFIX="$HOME/local/python311"
OPENSSL_PREFIX="$HOME/local/openssl111/lib"
QT515="$HOME/local/qt515"
PIP="$PREFIX/bin/python3.11 -m pip"

exec > >(tee -a "$LOG") 2>&1
echo "=== $(date) install_pip_fix.sh start ==="

export PATH="$PREFIX/bin:$PATH"
export LD_LIBRARY_PATH="$OPENSSL_PREFIX:${LD_LIBRARY_PATH:-}"

write_env() {
    cat > "$HOME/py/TempMonitor/dev/python311_env.sh" << EOF
# TempMonitor Python 3.11
export PATH="$PREFIX/bin:\$PATH"
export LD_LIBRARY_PATH="$OPENSSL_PREFIX:\${LD_LIBRARY_PATH:-}"
export QT515="$QT515"
EOF
    echo "Wrote python311_env.sh"
}

pip_retry() {
    $PIP install --default-timeout=180 --retries 5 "$@"
}

install_kivy_stack() {
    echo "--- pyqtgraph + kivy (no Qt binding yet) ---"
    pip_retry pyqtgraph 'kivy[base]' || return 1
}

install_qt515_if_needed() {
    if [ -x "$QT515/bin/qmake" ]; then
        echo "Qt 5.15 OK: $($QT515/bin/qmake -version | head -1)"
        return 0
    fi
    echo "--- building minimal Qt 5.15.16 (qtbase only, ~1-2 h) ---"
    sudo apt-get install -y --allow-unauthenticated \
        libxcb1-dev libxcb-xfixes0-dev libxcb-render0-dev \
        libxcb-render-util0-dev libxcb-shape0-dev libxcb-randr0-dev \
        libxcb-icccm4-dev libxcb-image0-dev libxcb-keysyms1-dev \
        libxcb-xinerama0-dev libfontconfig1-dev libfreetype6-dev \
        libdbus-1-dev libudev-dev libinput-dev libxkbcommon-dev \
        libx11-dev libx11-xcb-dev libxext-dev libxrender-dev \
        libgl1-mesa-dev libglib2.0-dev \
        2>&1 | tail -5 || true

    cd /tmp || return 1
    rm -rf qtbase-everywhere-src-5.15.16 qtbase-everywhere-src-5.15.16.tar.xz
    wget -q https://download.qt.io/official_releases/qt/5.15/5.15.16/submodules/qtbase-everywhere-src-5.15.16.tar.xz \
        || return 1
    tar xf qtbase-everywhere-src-5.15.16.tar.xz
    cd qtbase-everywhere-src-5.15.16 || return 1
    ./configure -prefix "$QT515" \
        -release -opensource -confirm-license \
        -nomake examples -nomake tests -nomake tools \
        -no-opengl -no-gtk -no-evdev -no-libudev -no-openssl \
        -qt-zlib -qt-libpng -qt-libjpeg \
        -platform offscreen \
        -skip wayland \
        || return 1
    make -j1 || return 1
    make install || return 1
    echo "Qt 5.15 installed to $QT515"
}

install_pyqt5() {
    echo "--- PyQt5 (NOT PySide) ---"
    export PATH="$QT515/bin:$PATH"
    export QT_SELECT=5
    pip_retry sip pyqt-builder PyQt5-sip
    pip_retry PyQt5 --config-settings "--confirm-license" \
        --config-settings "QMAKE=$QT515/bin/qmake" \
        || pip_retry PyQt5
}

write_env
pip_retry numpy 2>/dev/null || true
install_kivy_stack || echo "WARN: kivy/pyqtgraph had issues — retry manually"
install_qt515_if_needed && install_pyqt5 || echo "WARN: PyQt5 build failed — see log"

echo "=== pip list ==="
$PIP list | grep -iE 'kivy|pyqt|numpy|graph|sip' || true

echo "=== $(date) install_pip_fix.sh end ==="
