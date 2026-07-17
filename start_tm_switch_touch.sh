#!/bin/bash
# Launch touch-friendly switch to 7" DSI display.
export DISPLAY=:0
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
cd /home/pi/py/TempMonitor/dev
exec python3 tm_switch_touch_app.py "$@"
