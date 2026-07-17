#!/bin/bash
# Switch Raspberry Pi official 7" touch display (Gen 1.1) vs HDMI (Eizo).
# Run on Pi:
#   bash set_touch_display.sh status
#   sudo bash set_touch_display.sh touch    # then reboot
#   sudo bash set_touch_display.sh hdmi     # then reboot
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PI_USER="${SUDO_USER:-${USER:-pi}}"
PI_HOME="$(getent passwd "$PI_USER" 2>/dev/null | cut -d: -f6)"
if [ -z "$PI_HOME" ]; then
    PI_HOME="/home/pi"
fi
BOOT_CFG=/boot/config.txt
BOOT_BAK=/boot/config.txt.bak-pre-touch
KIVY_CFG="${PI_HOME}/.kivy/config.ini"
KIVY_SNIPPET="${SCRIPT_DIR}/kivy-config-input.snippet"
KIVY_ENV="${PI_HOME}/.config/tm_kivy_display.env"
KIVY_LAUNCHER="${SCRIPT_DIR}/start_tm_kivy_gui.sh"

usage() {
    echo "Usage: $0 {status|touch|hdmi}"
    exit 1
}

show_status() {
    echo "=== Display status ==="
    if command -v tvservice >/dev/null 2>&1; then
        tvservice -s 2>/dev/null || true
    fi
    echo "--- /boot/config.txt (relevant) ---"
    grep -E 'ignore_lcd|display_default_lcd|lcd_rotate|vc4-kms' "$BOOT_CFG" 2>/dev/null || true
    echo "--- Kivy display env ---"
    if [ -f "$KIVY_ENV" ]; then
        cat "$KIVY_ENV"
    else
        echo "(none — HDMI default)"
    fi
}

ensure_kivy_input() {
    mkdir -p "$(dirname "$KIVY_CFG")"
    if [ ! -f "$KIVY_CFG" ]; then
        printf '[input]\n' > "$KIVY_CFG"
    fi
    if ! grep -q 'provider=mtdev' "$KIVY_CFG" 2>/dev/null; then
        if grep -q '^\[input\]' "$KIVY_CFG" 2>/dev/null; then
            cat >> "$KIVY_CFG" << 'EOF'
mouse = mouse
mtdev_%(name)s = probesysfs,provider=mtdev
hid_%(name)s = probesysfs,provider=hidinput
EOF
        elif [ -f "$KIVY_SNIPPET" ]; then
            grep -v '^#' "$KIVY_SNIPPET" | grep -v '^$' >> "$KIVY_CFG"
        else
            cat >> "$KIVY_CFG" << 'EOF'
[input]
mouse = mouse
mtdev_%(name)s = probesysfs,provider=mtdev
hid_%(name)s = probesysfs,provider=hidinput
EOF
        fi
        chown "${PI_USER}:${PI_USER}" "$KIVY_CFG" 2>/dev/null || true
    fi
    if [ -f "${SCRIPT_DIR}/fix_kivy_config_ini.sh" ]; then
        bash "${SCRIPT_DIR}/fix_kivy_config_ini.sh" || true
    fi
}

set_kivy_touch_env() {
    mkdir -p "$(dirname "$KIVY_ENV")"
    cat > "$KIVY_ENV" << 'EOF'
# Written by set_touch_display.sh — sourced by start_tm_kivy_gui.sh
export KIVY_BCM_DISPMANX_ID=0
EOF
    chown "${PI_USER}:${PI_USER}" "$KIVY_ENV" 2>/dev/null || true
}

set_kivy_hdmi_env() {
    rm -f "$KIVY_ENV"
}

apply_touch() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "Bitte mit sudo ausfuehren: sudo bash $0 touch"
        exit 1
    fi
    if [ ! -f "$BOOT_BAK" ]; then
        cp -a "$BOOT_CFG" "$BOOT_BAK"
        echo "Backup: $BOOT_BAK"
    fi
    sed -i 's/^[[:space:]]*ignore_lcd=1/#ignore_lcd=1/' "$BOOT_CFG"
    if ! grep -q '^display_default_lcd=1' "$BOOT_CFG"; then
        echo 'display_default_lcd=1' >> "$BOOT_CFG"
    fi
    if ! grep -q '^lcd_rotate=' "$BOOT_CFG"; then
        echo 'lcd_rotate=2' >> "$BOOT_CFG"
    fi
    ensure_kivy_input
    set_kivy_touch_env
    if [ -f "${SCRIPT_DIR}/install_display_switch_desktop.sh" ]; then
        sudo -u "$PI_USER" bash "${SCRIPT_DIR}/install_display_switch_desktop.sh" || true
    fi
    echo "Touch-Display konfiguriert. Bitte reboot: sudo reboot"
}

apply_hdmi() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "Bitte mit sudo ausfuehren: sudo bash $0 hdmi"
        exit 1
    fi
    if [ -f "$BOOT_BAK" ]; then
        cp -a "$BOOT_BAK" "$BOOT_CFG"
        echo "config.txt aus Backup wiederhergestellt."
    else
        if grep -q '^#ignore_lcd=1' "$BOOT_CFG"; then
            sed -i 's/^#ignore_lcd=1/ignore_lcd=1/' "$BOOT_CFG"
        elif ! grep -q '^ignore_lcd=1' "$BOOT_CFG"; then
            echo 'ignore_lcd=1' >> "$BOOT_CFG"
        fi
        sed -i '/^display_default_lcd=1/d' "$BOOT_CFG"
    fi
    set_kivy_hdmi_env
    if [ -f "${SCRIPT_DIR}/install_display_switch_desktop.sh" ]; then
        sudo -u "$PI_USER" bash "${SCRIPT_DIR}/install_display_switch_desktop.sh" || true
    fi
    echo "HDMI-Modus konfiguriert. Bitte reboot: sudo reboot"
}

CMD="${1:-status}"
case "$CMD" in
    status) show_status ;;
    touch)  apply_touch ;;
    hdmi)   apply_hdmi ;;
    *)      usage ;;
esac
