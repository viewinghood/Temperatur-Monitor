#!/bin/bash
# TempMonitor — build Python 3.11.11 + pip packages on Pi 3 (Stretch armhf)
# Log: ~/py/TempMonitor/dev/install_python311.log

LOG="$HOME/py/TempMonitor/dev/install_python311.log"
PREFIX="$HOME/local/python311"
OPENSSL_PREFIX="$HOME/local/openssl111"
PYVER=3.11.11
SWAPFILE=/swapfile311

exec > >(tee -a "$LOG") 2>&1
echo "=== $(date) install_python311.sh start ==="

die() { echo "FATAL: $*"; exit 1; }

fix_apt() {
    if [ "${SKIP_APT:-0}" = "1" ]; then
        echo "SKIP_APT=1 — skipping apt"
        return
    fi
    if grep -q 'raspbian.raspberrypi.org/raspbian' /etc/apt/sources.list 2>/dev/null; then
        sudo sed -i 's|raspbian.raspberrypi.org/raspbian|archive.raspbian.org/raspbian|g' \
            /etc/apt/sources.list || true
    fi
    sudo apt-get update -o Acquire::Languages=none 2>&1 | tail -5 || true
}

ensure_swap() {
    SWAPON=/sbin/swapon
    MKSWAP=/sbin/mkswap
    if [ ! -x "$SWAPON" ]; then
        echo "WARN: $SWAPON missing — continuing without extra swap"
        return
    fi
    if "$SWAPON" --show | grep -q "$SWAPFILE"; then
        echo "Swap already active: $SWAPFILE"
        return
    fi
    if [ ! -f "$SWAPFILE" ]; then
        echo "Creating 1G swap at $SWAPFILE"
        sudo dd if=/dev/zero of="$SWAPFILE" bs=1M count=1024 status=progress
        sudo chmod 600 "$SWAPFILE"
        sudo "$MKSWAP" "$SWAPFILE"
    fi
    sudo "$SWAPON" "$SWAPFILE" && echo "Swap enabled: $SWAPFILE" || echo "WARN: swapon failed"
    free -m | grep -E 'Mem|Swap'
}

install_build_deps() {
    if [ "${SKIP_APT:-0}" = "1" ]; then
        return
    fi
    sudo apt-get install -y --allow-unauthenticated \
        build-essential libffi-dev zlib1g-dev libbz2-dev libreadline-dev \
        libsqlite3-dev libncurses5-dev liblzma-dev libexpat1-dev \
        libssl-dev wget ca-certificates util-linux \
        2>&1 | tail -10 || echo "WARN: apt install had errors"
}

build_openssl() {
    if [ -x "$OPENSSL_PREFIX/bin/openssl" ]; then
        echo "OpenSSL OK: $("$OPENSSL_PREFIX/bin/openssl" version)"
        return
    fi
    cd /tmp || die "no /tmp"
    rm -rf openssl-1.1.1w openssl-1.1.1w.tar.gz
    wget -q https://www.openssl.org/source/openssl-1.1.1w.tar.gz || die "openssl download failed"
    tar xzf openssl-1.1.1w.tar.gz
    cd openssl-1.1.1w || die "openssl extract failed"
    # -O0 avoids gcc 6.3 ICE on Pi 3; no-asm reduces ARM asm edge cases
    ./config --prefix="$OPENSSL_PREFIX" --openssldir="$OPENSSL_PREFIX" shared no-asm
    make -j1 CFLAGS='-O0 -g0' || die "openssl make failed"
    make install || die "openssl install failed"
    echo "OpenSSL installed: $("$OPENSSL_PREFIX/bin/openssl" version)"
}

build_python() {
    if [ -x "$PREFIX/bin/python3.11" ]; then
        echo "Python OK: $("$PREFIX/bin/python3.11" --version)"
        return
    fi
    cd /tmp || die "no /tmp"
    rm -rf "Python-$PYVER" "Python-$PYVER.tgz"
    wget -q "https://www.python.org/ftp/python/$PYVER/Python-$PYVER.tgz" || die "python download failed"
    tar xzf "Python-$PYVER.tgz"
    cd "Python-$PYVER" || die "python extract failed"
    export LDFLAGS="-Wl,-rpath,$OPENSSL_PREFIX/lib"
    export CPPFLAGS="-I$OPENSSL_PREFIX/include"
    export LD_LIBRARY_PATH="$OPENSSL_PREFIX/lib:${LD_LIBRARY_PATH:-}"
    ./configure --prefix="$PREFIX" \
        --with-openssl="$OPENSSL_PREFIX" \
        --with-system-ffi \
        --disable-test-modules || die "python configure failed"
    make -j1 || die "python make failed"
    make altinstall || die "python altinstall failed"
    echo "Python installed: $("$PREFIX/bin/python3.11" --version)"
}

install_pip_packages() {
    export LD_LIBRARY_PATH="$OPENSSL_PREFIX/lib:${LD_LIBRARY_PATH:-}"
    "$PREFIX/bin/python3.11" -m ensurepip --upgrade || die "ensurepip failed"
    "$PREFIX/bin/python3.11" -m pip install --upgrade pip setuptools wheel || die "pip upgrade failed"
    "$PREFIX/bin/python3.11" -m pip install \
        --extra-index-url https://www.piwheels.org/simple \
        'numpy>=1.23' 'pyqtgraph>=0.13' 'PyQt5>=5.15' 'kivy[base]>=2.2' \
        || "$PREFIX/bin/python3.11" -m pip install \
            'numpy>=1.23' 'pyqtgraph>=0.13' 'PyQt5>=5.15' 'kivy[base]>=2.2' \
        || die "pip packages failed"
    echo "=== pip packages ==="
    "$PREFIX/bin/python3.11" -m pip list | grep -iE 'kivy|pyqt|numpy|graph'
}

write_profile_snippet() {
    SNIP="$HOME/py/TempMonitor/dev/python311_env.sh"
    cat > "$SNIP" << EOF
# TempMonitor Python 3.11 environment
export PATH="$PREFIX/bin:\$PATH"
export LD_LIBRARY_PATH="$OPENSSL_PREFIX/lib:\${LD_LIBRARY_PATH:-}"
EOF
    echo "Wrote $SNIP"
}

fix_apt
ensure_swap
install_build_deps
build_openssl
build_python
install_pip_packages
write_profile_snippet

echo "=== $(date) install_python311.sh DONE ==="
