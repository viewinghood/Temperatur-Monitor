#!/bin/bash
# Stretch-like Raspberry Pi desktop on Bullseye Lite (curated, no browser bloat).
# Run on Pi: bash ~/py/TempMonitor/dev/install_bullseye_desktop.sh
set -e
LOG="$HOME/py/TempMonitor/dev/install_bullseye_desktop.log"
DEV="$HOME/py/TempMonitor/dev"
exec >> "$LOG" 2>&1

echo "=== $(date) install_bullseye_desktop.sh pid=$$ ==="
export DEBIAN_FRONTEND=noninteractive

if [ ! -f /etc/apt/apt.conf.d/99force-ipv4 ]; then
    echo 'Acquire::ForceIPv4 "true";' | sudo tee /etc/apt/apt.conf.d/99force-ipv4 >/dev/null
fi

echo "--- apt update ---"
sudo apt-get update -qq

echo "--- desktop packages ---"
sudo apt-get install -y --no-install-recommends \
    rc-gui \
    pipanel \
    pishutdown \
    lxplug-cputemp \
    lxplug-ejecter \
    lxplug-network \
    lxplug-volumepulse \
    lxplug-menu \
    lxplug-bluetooth \
    gtk2-engines-pixflat \
    pixflat-icons \
    lxappearance \
    lxinput \
    obconf \
    xcompmgr \
    synaptic \
    thonny \
    geany \
    git \
    scrot \
    galculator \
    gpicview \
    evince \
    htop \
    tree \
    vim \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    zip \
    unzip

echo "--- lxpanel Pi defaults ---"
mkdir -p "$HOME/.config/lxpanel/LXDE-pi/panels"
if [ ! -s "$HOME/.config/lxpanel/LXDE-pi/panels/panel" ]; then
    cp /etc/xdg/lxpanel/LXDE-pi/panels/panel \
        "$HOME/.config/lxpanel/LXDE-pi/panels/panel"
fi

echo "--- TempMonitor desktop shortcut ---"
mkdir -p "$HOME/Desktop"
cat > "$HOME/Desktop/TempMonitor.desktop" << 'EOF'
[Desktop Entry]
Name=TempMonitor
Comment=4-Kanal Temperatur Monitor
Exec=/home/pi/py/TempMonitor/dev/start_tm_gui.sh
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=Science;
EOF
chmod +x "$HOME/Desktop/TempMonitor.desktop"

echo "--- CPU usage panel (Stretch-style, top-right) ---"
bash "$DEV/install_panel_cpu.sh"

echo "--- menu count ---"
ls /usr/share/applications/*.desktop 2>/dev/null | wc -l

date > "$DEV/READY_bullseye_desktop.txt"
echo "Stretch-like desktop packages OK" >> "$DEV/READY_bullseye_desktop.txt"
echo "=== $(date) DONE (reboot or re-login for full panel) ==="
