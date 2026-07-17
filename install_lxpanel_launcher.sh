#!/bin/bash
# Add TempMonitor (Touch) to lxpanel launch bar — reliable single-tap start.
set -e

PANEL="$HOME/.config/lxpanel/LXDE-pi/panels/panel"
MARKER="TempMonitor-Touch.desktop"

if [ ! -f "$PANEL" ]; then
    echo "lxpanel: config not found, skip."
    exit 0
fi

if grep -q "$MARKER" "$PANEL"; then
    echo "lxpanel: TempMonitor launcher already present."
else
    cp "$PANEL" "${PANEL}.bak-tm"
    sed -i "/id=lxterminal.desktop/a\\
    Button {\\
      id=${MARKER}\\
    }" "${PANEL}.bak-tm"
    mv "${PANEL}.bak-tm" "$PANEL"
    echo "lxpanel: added ${MARKER} to launch bar (next to Terminal)."
fi

if command -v lxpanelctl >/dev/null 2>&1; then
    lxpanelctl restart 2>/dev/null || true
fi
