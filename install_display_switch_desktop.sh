#!/bin/bash
# Install both display-switch desktop icons + passwordless sudo.
# Run once on Pi: bash ~/py/TempMonitor/dev/install_display_switch_desktop.sh
set -e

DEV="$HOME/py/TempMonitor/dev"
SUDOERS=/etc/sudoers.d/tm-display-switch

chmod +x \
    "$DEV/set_touch_display.sh" \
    "$DEV/start_tm_switch_hdmi.sh" \
    "$DEV/start_tm_switch_touch.sh"

cp "$DEV/SwitchToHDMI.desktop" "$HOME/Desktop/SwitchToHDMI.desktop"
cp "$DEV/SwitchToTouch.desktop" "$HOME/Desktop/SwitchToTouch.desktop"
chmod 644 "$HOME/Desktop/SwitchToHDMI.desktop" "$HOME/Desktop/SwitchToTouch.desktop"

sudo tee "$SUDOERS" >/dev/null << EOF
# TempMonitor: display switch without password prompt (pi user)
pi ALL=(ALL) NOPASSWD: $DEV/set_touch_display.sh touch
pi ALL=(ALL) NOPASSWD: $DEV/set_touch_display.sh hdmi
pi ALL=(ALL) NOPASSWD: /sbin/reboot
pi ALL=(ALL) NOPASSWD: /usr/sbin/reboot
EOF
sudo chmod 440 "$SUDOERS"
sudo visudo -cf "$SUDOERS"

echo "Desktop icons:"
echo "  $HOME/Desktop/SwitchToTouch.desktop  (HDMI -> 7\" touch)"
echo "  $HOME/Desktop/SwitchToHDMI.desktop    (7\" touch -> HDMI)"
