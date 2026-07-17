# Safe Boot Fix — Pi 3 Bullseye Desktop Image

## Why boot failed

| Symptom | Cause |
|---------|--------|
| **Dependency failed for Light Display Manager** | `lightdm` needs working X/KMS display — failed on Pi 3 + Eizo |
| **device descriptor read error** | USB at boot (keyboard, touch, hub) or **weak power supply** |
| **ignore_lcd + vc4-kms-v3d** | Display stack conflict (first fix) |

**Desktop image on Pi 3** = fragile. TempMonitor needs **SSH + SPI**, not LightDM.

## Fix applied (`fix_safe_boot.ps1`)

1. **`systemd.unit=multi-user.target`** in `cmdline.txt` → **no GUI**, no LightDM
2. **`vc4-fkms-v3d`** instead of full KMS (Pi 3 stable)
3. **`display_auto_detect=0`** — no DSI probe at boot
4. SPI, I2C, UART unchanged
5. SSH + authorized_keys

## Before booting Pi

- **Official 5V/2.5A+ PSU** (not PC USB)
- **Unplug all USB** except nothing (or only keyboard after first success)
- **HDMI Eizo** connected
- **7" touch unplugged** for now

## After stable boot

```bash
ssh raspi          # SSH key preferred; change default OS password after first login
sudo systemctl get-default   # → multi-user.target
ls /dev/spidev*    # SPI
i2cdetect -y 1     # I2C
```

GUI/Kivy later: install on demand or switch to Lite image.

## Plan B — most reliable

Reflash **Raspberry Pi OS Lite Bullseye 32-bit** (no desktop, no lightdm ever).
Image: `2023-05-03-raspios-bullseye-armhf-lite.img.xz`
