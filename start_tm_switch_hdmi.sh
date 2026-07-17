#!/bin/bash
# Launch touch-friendly HDMI switch app (7" DSI -> Eizo HDMI).
export DISPLAY=:0
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
cd /home/pi/py/TempMonitor/dev

if [ -f "${HOME}/.config/tm_kivy_display.env" ]; then
    # shellcheck source=/dev/null
    . "${HOME}/.config/tm_kivy_display.env"
fi

exec python3 tm_switch_hdmi_app.py "$@"
