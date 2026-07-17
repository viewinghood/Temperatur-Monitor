#!/bin/bash
# Add CPU usage monitor to lxpanel (top-right, like Stretch desktop).
set -e
PANEL="$HOME/.config/lxpanel/LXDE-pi/panels/panel"
mkdir -p "$(dirname "$PANEL")"

if [ ! -f "$PANEL" ]; then
    cp /etc/xdg/lxpanel/LXDE-pi/panels/panel "$PANEL"
fi

cp "$PANEL" "${PANEL}.bak-$(date +%Y%m%d)"

if grep -q 'type=cpu' "$PANEL"; then
    echo "CPU-Auslastungsanzeige ist bereits in der Panel-Konfiguration."
else
    python3 << 'PY'
from pathlib import Path

panel = Path.home() / '.config/lxpanel/LXDE-pi/panels/panel'
text = panel.read_text()
block = """Plugin {
  type=space
  Config {
    Size=2
  }
}
Plugin {
  type=cpu
  Config {
  }
}
"""
marker = "Plugin {\n  type=dclock"
if marker not in text:
    raise SystemExit('dclock-Plugin nicht gefunden — Panel manuell pruefen.')
panel.write_text(text.replace(marker, block + marker, 1))
print('CPU-Auslastungsanzeige vor der Uhr eingefuegt.')
PY
fi

DISPLAY=:0 lxpanelctl restart 2>/dev/null || true
echo "Panel neu geladen. Bei Bedarf abmelden/anmelden."
