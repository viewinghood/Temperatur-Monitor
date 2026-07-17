#!/bin/bash
# Repair ~/.kivy/config.ini — merge duplicate [input] sections (touch display setup).
set -e

PI_USER="${SUDO_USER:-${USER:-pi}}"
PI_HOME="$(getent passwd "$PI_USER" 2>/dev/null | cut -d: -f6)"
if [ -z "$PI_HOME" ]; then
    PI_HOME="/home/pi"
fi
CFG="${PI_HOME}/.kivy/config.ini"

if [ ! -f "$CFG" ]; then
    exit 0
fi

python3 - "$CFG" << 'PY'
import sys

path = sys.argv[1]
with open(path, encoding='utf-8', errors='replace') as fp:
    lines = fp.readlines()

out = []
input_keys = {}
input_open = False
input_header_written = False
pending = []

def flush_pending():
    global pending
    for line in pending:
        key = line.split('=', 1)[0].strip()
        if key and key not in input_keys:
            input_keys[key] = line
            out.append(line)
    pending = []

for line in lines:
    stripped = line.strip()
    if stripped == '[input]':
        if not input_header_written:
            out.append(line)
            input_header_written = True
            input_open = True
        else:
            input_open = True
        continue
    if stripped.startswith('[') and stripped.endswith(']'):
        if input_open:
            flush_pending()
            input_open = False
        out.append(line)
        continue
    if input_open:
        if not stripped or stripped.startswith('#') or stripped.startswith(';'):
            flush_pending()
            out.append(line)
        elif '=' in line:
            pending.append(line)
        else:
            flush_pending()
            out.append(line)
        continue
    out.append(line)

if input_open:
    flush_pending()

with open(path, 'w', encoding='utf-8') as fp:
    fp.writelines(out)
PY

chown "${PI_USER}:${PI_USER}" "$CFG" 2>/dev/null || true
