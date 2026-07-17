#!/bin/bash
# Trust desktop launchers for single-tap start (no Execute dialog).
# Run on Pi: bash ~/py/TempMonitor/dev/install_touch_desktop.sh
set -e

DEV="$HOME/py/TempMonitor/dev"
DESKTOP="$HOME/Desktop"
APPS="$HOME/.local/share/applications"
PCMANFM_CONF="$HOME/.config/pcmanfm/LXDE-pi/pcmanfm.conf"
LIBFM_CONF="$HOME/.config/libfm/libfm.conf"
ICON_SRC="/usr/share/icons/PiXflat/48x48/apps/utilities-system-monitor.png"
ICON_DST="$DEV/icons/tempmonitor-48.png"

chmod +x \
    "$DEV/start_tm_pyqt_touch_gui.sh" \
    "$DEV/start_tm_kivy_gui.sh" \
    "$DEV/start_tm_gui.sh" \
    "$DEV/start_tm_switch_hdmi.sh" \
    "$DEV/start_tm_switch_touch.sh" \
    "$DEV/set_touch_display.sh" \
    "$DEV/launch_tm_hdmi.py" \
    "$DEV/launch_tm_touch.py" \
    "$DEV/install_lxpanel_launcher.sh"

mkdir -p "$DEV/icons"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$ICON_DST"
fi

mkdir -p "$APPS"
for name in TempMonitor TempMonitor-Touch SwitchToHDMI SwitchToTouch; do
    src="$DEV/${name}.desktop"
    [ -f "$src" ] || continue
    install -m 644 "$src" "$DESKTOP/${name}.desktop"
    install -m 644 "$src" "$APPS/${name}.desktop"
done

# Remove legacy Kivy desktop icon (confusing duplicate).
rm -f "$DESKTOP/TempMonitor-Kivy.desktop"

# pcmanfm.conf had duplicate [config] blocks — merge single_click into first block only.
if [ -f "$PCMANFM_CONF" ]; then
    awk '
        BEGIN { in_config=0; added=0 }
        /^\[/ {
            if ($0 == "[config]") {
                in_config=1
                print
                if (!added) { print "single_click=1"; added=1 }
                next
            }
            in_config=0
        }
        in_config && /^single_click=/ { next }
        { print }
    ' "$PCMANFM_CONF" > "${PCMANFM_CONF}.tmp"
    mv "${PCMANFM_CONF}.tmp" "$PCMANFM_CONF"
fi

if [ -f "$LIBFM_CONF" ]; then
    for kv in 'single_click=1' 'quick_exec=1'; do
        key="${kv%%=*}"
        val="${kv#*=}"
        if grep -q "^${key}=" "$LIBFM_CONF"; then
            sed -i "s/^${key}=.*/${key}=${val}/" "$LIBFM_CONF"
        else
            sed -i "/^\[config\]/a ${key}=${val}" "$LIBFM_CONF"
        fi
    done
fi

fix_desktop_file() {
    local f="$1"
    [ -f "$f" ] || return 0
    chmod 644 "$f"
    gio set "$f" metadata::trusted true 2>/dev/null || true
}

for f in "$DESKTOP"/*.desktop "$APPS"/*.desktop; do
    fix_desktop_file "$f"
done

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS" 2>/dev/null || true
fi

if [ -f "$DEV/install_display_switch_desktop.sh" ]; then
    bash "$DEV/install_display_switch_desktop.sh"
fi

if [ -f "$DEV/install_lxpanel_launcher.sh" ]; then
    bash "$DEV/install_lxpanel_launcher.sh"
fi

DISPLAY="${DISPLAY:-:0}" pcmanfm --desktop --profile LXDE-pi --reconfigure 2>/dev/null || true
pkill -HUP pcmanfm 2>/dev/null || true

echo "Desktop launchers (644, icon, lxpanel):"
ls -la "$DESKTOP"/*.desktop 2>/dev/null || true
