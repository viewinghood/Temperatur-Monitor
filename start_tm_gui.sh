#!/bin/bash
# Start TempMonitor PyQt GUI on the HDMI desktop (auto-login session).
export DISPLAY=:0
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
cd /home/pi/py/TempMonitor/dev

if pgrep -f 'python3 tm_pyqt_plot_app.py' >/dev/null 2>&1; then
    echo "TempMonitor laeuft bereits (PID $(pgrep -f 'python3 tm_pyqt_plot_app.py' | head -1))."
    exit 0
fi
if pgrep -f 'python3 tm_kivy_plot_app.py' >/dev/null 2>&1; then
    echo "Beende alte Kivy-Instanz …"
    pkill -f 'python3 tm_kivy_plot_app.py' || true
    sleep 1
fi

exec python3 tm_pyqt_plot_app.py "$@"
