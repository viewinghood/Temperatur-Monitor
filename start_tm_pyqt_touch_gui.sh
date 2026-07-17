#!/bin/bash
# Start TempMonitor PyQt touch UI (7" DSI — replaces Kivy, native OpenGL plot).
export DISPLAY=:0
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
LOG="${HOME}/py/TempMonitor/dev/tm_pyqt_touch_gui.log"

if [ -f "${HOME}/.config/tm_kivy_display.env" ]; then
    # shellcheck source=/dev/null
    . "${HOME}/.config/tm_kivy_display.env"
fi

if pgrep -f 'python3 tm_pyqt_touch_app.py' >/dev/null 2>&1; then
    echo "TempMonitor Touch laeuft bereits (PID $(pgrep -f 'python3 tm_pyqt_touch_app.py' | head -1))."
    exit 0
fi

for pat in 'python3 tm_kivy_app.py' 'python3 tm_pyqt_plot_app.py'; do
    if pgrep -f "$pat" >/dev/null 2>&1; then
        echo "Beende andere TempMonitor-Instanz ($pat) …"
        pkill -f "$pat" || true
        sleep 1
    fi
done

exec python3 tm_pyqt_touch_app.py "$@" >>"$LOG" 2>&1
