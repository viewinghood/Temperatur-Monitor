# Bullseye SD — Boot-Konfiguration (nach Etcher + Migration)
# Erstellt: 2026-07-06

## Image
- Raspberry Pi OS **Bullseye 32-bit (Desktop)**, 2023-05-03
- Geflasht mit Balena Etcher auf 64 GB SD

## Boot-Partition (I: nach Flash)
- `ssh` — SSH beim ersten Boot aktiv
- `authorized_keys` — your SSH public key (Ed25519)
- `config.txt` — Hardware von Stretch-Pi übernommen (siehe unten)

## Von Stretch-Pi übernommen (`/boot/config.txt`)

| Setting | Wert | Zweck |
|---------|------|--------|
| `dtparam=i2c_arm=on` | an | I2C |
| `dtparam=spi=on` | an | ADS1118 SPI |
| `dtparam=audio=on` | an | Audio |
| `enable_uart=1` | an | Serial |
| `dtoverlay=pi3-miniuart-bt` | neu | UART auf GPIO (BT auf mini-UART) |
| `ignore_lcd=1` | an | **HDMI Eizo** primär, 7" DSI aus |
| `lcd_rotate=2` | an | Touch-LCD 180° (für später) |
| `disable_overscan=0` | an | wie Stretch |
| `gpu_mem=128` | an | GPU-RAM für Display |

**Bewusst NICHT übernommen:**
- `start_x=0` — Stretch hatte kein Desktop; Bullseye-Desktop soll auf HDMI laufen
- `dtoverlay=vc4-kms-v3d` — auf Pi 3 vorerst aus (Legacy/Kivy-Kompatibilität prüfen)

## SSH (development PC)
```
Host raspi
  HostName <PI_IP>   # set after first boot
  User pi
  IdentityFile ~/.ssh/id_ed25519
```
After first login: **change the default OS password immediately** (`passwd`). Never commit passwords.

## Stretch-Backup (local only, not in public GitHub)
`pi_stretch_backup/` on the development machine — keep offline.

## Nächste Schritte
1. SD in Pi 3 stecken, booten (HDMI-Monitor anschließen)
2. Ersten Boot abwarten (~2–5 Min), IP ermitteln (Router oder `arp -a`)
3. `ssh raspi` testen
4. Projekt nach `/home/pi/py/TempMonitor/dev/` deployen
5. `apt update && apt install` — Python3, pip, kivy, spi-tools …
