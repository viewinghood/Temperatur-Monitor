#!/bin/bash
# Nacht-Monitor: alle 30 min Status, bei Fehler install_pyqt5.sh neu starten
# Log: ~/py/TempMonitor/dev/night_monitor.log

DEV="$HOME/py/TempMonitor/dev"
LOG="$DEV/night_monitor.log"
INTERVAL=1800   # 30 min
PREFIX="$HOME/local/python311"
OPENSSL="$HOME/local/openssl111/lib"
QT_SRC=/tmp/qtbase-everywhere-src-5.15.16

export PATH="$PREFIX/bin:$PATH"
export LD_LIBRARY_PATH="$OPENSSL:$LD_LIBRARY_PATH"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }

check_ready() {
    [ -f "$DEV/READY_py311_gui.txt" ] && return 0
    python3.11 -c "import PyQt5.QtWidgets; import pyqtgraph; import kivy" 2>/dev/null
}

write_env() {
    cat > "$DEV/python311_env.sh" << EOF
# TempMonitor Python 3.11
export PATH="$PREFIX/bin:\$PATH"
export LD_LIBRARY_PATH="$OPENSSL:\${LD_LIBRARY_PATH:-}"
export QT515="$HOME/local/qt515"
export QT_QPA_PLATFORM=offscreen
EOF
}

restart_install() {
    # Kein zweiter Start wenn schon einer läuft
    if pgrep -f "install_pyqt5.sh" >/dev/null; then
        log "install_pyqt5 already running — skip restart"
        return
    fi
    if [ -f "$DEV/install.lock" ] && fuser "$DEV/install.lock" >/dev/null 2>&1; then
        log "install.lock held — skip restart"
        return
    fi
    log "RESTART install_pyqt5.sh"
    nohup flock -n "$DEV/install.lock" "$DEV/install_pyqt5.sh" >> "$DEV/install_pyqt5.log" 2>&1 &
}

is_build_running() {
    pgrep -f "install_pyqt5.sh" >/dev/null && return 0
    pgrep -f "qtbase-everywhere-src-5.15.16" >/dev/null && return 0
    [ -d "$QT_SRC" ] && pgrep -f "make.*qtbase" >/dev/null && return 0
    return 1
}

log "=== night_monitor start (interval ${INTERVAL}s) ==="
write_env

while true; do
    if check_ready; then
        log "READY — PyQt5+Kivy+pyqtgraph OK"
        echo "$(date '+%Y-%m-%d %H:%M:%S') READY" > "$DEV/BUILD_STATUS.txt"
        write_env
        python3.11 -m pip list 2>/dev/null | grep -iE 'kivy|pyqt|graph|numpy' >> "$LOG"
        exit 0
    fi

    if is_build_running; then
        phase="unknown"
        [ -x "$HOME/local/qt515/bin/qmake" ] && phase="qt515_done_pyqt5_pending"
        [ -d "$QT_SRC" ] && [ -f "$QT_SRC/Makefile" ] && phase="qt_make_running"
        log "BUILD running phase=$phase"
        echo "$(date '+%Y-%m-%d %H:%M:%S') RUNNING phase=$phase" > "$DEV/BUILD_STATUS.txt"
        tail -1 "$DEV/install_pyqt5.log" 2>/dev/null | head -c 120 >> "$LOG" || true
        echo >> "$LOG"
    else
        # Crashed or never started?
        if tail -5 "$DEV/install_pyqt5.log" 2>/dev/null | grep -q FATAL; then
            log "FATAL detected — restarting"
        else
            log "No build process — starting/restarting"
        fi
        restart_install
    fi

    free -m | awk '/Mem:|Swap:/ {print}' >> "$LOG"
    sleep "$INTERVAL"
done
