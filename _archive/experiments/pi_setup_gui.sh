#!/bin/bash
# Bullseye Lite -> Desktop autologin (Stretch-style). Keep legacy HDMI config.
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== 1) cmdline: remove forced multi-user ==="
sudo sed -i 's/ systemd\.unit=multi-user\.target//g' /boot/cmdline.txt
grep -q ' logo.nologo' /boot/cmdline.txt || true

echo "=== 2) config: enable GPU for desktop ==="
sudo sed -i 's/^start_x=0$/#start_x=0  # disabled for desktop GUI/' /boot/config.txt

echo "=== 3) install desktop (may take 10-20 min on Pi 3) ==="
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    raspberrypi-ui-mods \
    lightdm \
    xserver-xorg \
    xinit \
    lxde-core \
    lxterminal \
    2>&1 | tail -5

echo "=== 4) desktop autologin pi (B4) ==="
sudo raspi-config nonint do_boot_behaviour B4
sudo sed -i 's/^autologin-user=.*/autologin-user=pi/' /etc/lightdm/lightdm.conf

echo "=== 5) verify ==="
systemctl get-default
grep autologin-user /etc/lightdm/lightdm.conf | grep -v '^#' | head -1
grep start_x /boot/config.txt || true
cat /boot/cmdline.txt

echo "=== DONE — reboot manually ==="
