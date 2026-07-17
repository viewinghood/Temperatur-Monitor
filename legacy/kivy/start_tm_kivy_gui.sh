#!/bin/bash
# Start TempMonitor Kivy touch UI (Entwurf — not the default desktop icon).
export DISPLAY=:0
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
LOG="${HOME}/py/TempMonitor/dev/tm_kivy_gui.log"

# Optional: set by set_touch_display.sh touch (DSI LCD)
if [ -f "${HOME}/.config/tm_kivy_display.env" ]; then
    # shellcheck source=/dev/null
    . "${HOME}/.config/tm_kivy_display.env"
fi

if [ -f "${SCRIPT_DIR}/fix_kivy_config_ini.sh" ]; then
    bash "${SCRIPT_DIR}/fix_kivy_config_ini.sh" 2>/dev/null || true
fi

if pgrep -f 'python3 tm_kivy_app.py' >/dev/null 2>&1; then
    echo "TempMonitor Kivy laeuft bereits (PID $(pgrep -f 'python3 tm_kivy_app.py' | head -1))."
    exit 0
fi

# SPI is exclusive — stop PyQt instance if running.
if pgrep -f 'python3 tm_pyqt_plot_app.py' >/dev/null 2>&1; then
    echo "Beende PyQt TempMonitor (SPI freigeben) …"
    pkill -f 'python3 tm_pyqt_plot_app.py' || true
    sleep 1
fi

exec python3 tm_kivy_app.py "$@" >>"$LOG" 2>&1
