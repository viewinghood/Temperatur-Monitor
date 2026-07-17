#!/bin/bash
# Stretch-style boot fsck on Bullseye Lite:
#   - visible check on HDMI (console=tty1, no logo.nologo, rootdelay)
#   - periodic ext4 fsck (mount count + time interval)
#   - optional one-time force fsck on next reboot
#
# Run on Pi:  sudo bash ~/py/TempMonitor/dev/install_bullseye_boot_fsck.sh
#             sudo bash install_bullseye_boot_fsck.sh --force-next-boot
set -e

FORCE_NEXT=0
if [ "${1:-}" = '--force-next-boot' ]; then
    FORCE_NEXT=1
fi

BOOT_CMDLINE=/boot/cmdline.txt
ROOT_DEV=$(findmnt -n -o SOURCE /)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="${SCRIPT_DIR}/install_bullseye_boot_fsck.log"
READY="${SCRIPT_DIR}/READY_bullseye_boot_fsck.txt"

exec >> "$LOG" 2>&1
echo "=== $(date) install_bullseye_boot_fsck.sh pid=$$ ==="
echo "ROOT_DEV=$ROOT_DEV"

if [ "$(id -u)" -ne 0 ]; then
    echo "Bitte mit sudo ausfuehren."
    exit 1
fi

# --- /boot/cmdline.txt (Stretch reference in pi_stretch_backup/boot/cmdline.txt) ---
cp -a "$BOOT_CMDLINE" "${BOOT_CMDLINE}.bak-$(date +%Y%m%d)"

LINE=$(tr -d '\n' < "$BOOT_CMDLINE")

# Remove logo.nologo — hides boot text / fsck progress on HDMI.
LINE=$(echo "$LINE" | sed 's/ logo\.nologo//g')

# Stretch had rootdelay=5 — short pause so fsck messages stay readable.
if ! echo "$LINE" | grep -q 'rootdelay='; then
    LINE="${LINE} rootdelay=5"
fi

# Ensure repair on errors (Stretch + Bullseye).
if ! echo "$LINE" | grep -q 'fsck.repair='; then
    LINE="${LINE} fsck.repair=yes"
fi

# auto = check when fstab pass=1 and interval/count due (default, explicit).
if ! echo "$LINE" | grep -q 'fsck.mode='; then
    LINE="${LINE} fsck.mode=auto"
fi

echo "$LINE" > "$BOOT_CMDLINE"
echo "cmdline.txt updated:"
cat "$BOOT_CMDLINE"
echo

# --- /etc/fstab: root pass=1 (fsck on boot when due) ---
if grep -q 'PARTUUID=.*/ ext4' /etc/fstab; then
    sed -i 's|\(PARTUUID=[^ ]\+[[:space:]]\+/[[:space:]]\+ext4[[:space:]]\+[^[:space:]]\+[[:space:]]\+[^[:space:]]\+[[:space:]]\+\)[0-9]|\\11|' /etc/fstab
    echo "fstab root pass field set to 1"
    grep ' ext4 ' /etc/fstab || true
else
    echo "WARN: fstab root line not found — bitte manuell pass=1 pruefen"
fi
echo

# --- tune2fs: periodic checks (Bullseye image often has both disabled: -1 / 0) ---
# Stretch/Raspbian classic: every 30 mounts OR every 6 months.
tune2fs -c 30 -i 6m "$ROOT_DEV"
echo "tune2fs after:"
tune2fs -l "$ROOT_DEV" | grep -E 'Mount count|Maximum mount|Check interval|Last checked|Filesystem state'
echo

if [ "$FORCE_NEXT" -eq 1 ]; then
  # Force fsck on next boot (one time).
  tune2fs -C 31 "$ROOT_DEV"
  echo "Next reboot will run fsck (mount count forced above maximum)."
fi

date > "$READY"
echo "Stretch-style boot fsck OK — reboot to verify on HDMI." >> "$READY"
echo "=== $(date) DONE ==="
