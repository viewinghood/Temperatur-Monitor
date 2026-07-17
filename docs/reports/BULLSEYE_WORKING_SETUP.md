# Bullseye Lite — funktionierende Konfiguration (Pi 3 + Eizo HDMI)

Stand: 2026-07-07 — TempMonitor läuft, Plot OK, ein Fenster, ~28 °C mit Platine.

## Image (bewusst Lite, nicht Desktop-Full)

| | |
|---|---|
| Image | `2023-05-03-raspios-bullseye-armhf-lite.img` |
| Grund | **Desktop-Full-Image** verursachte LightDM/KMS-Probleme auf Pi 3 + Eizo |
| Desktop | Manuell: `lxde-core` + `lightdm` + `raspberrypi-ui-mods` |
| Python | **3.9.2** aus apt (kein 3.11-Source-Build) |

## Display — was funktioniert (Stretch-Stil)

**Wichtig:** Monitor per **Auto-EDID** verhandeln lassen — wie auf Stretch.

Datei: `/boot/config.txt` (Backup: `pi_bullseye_backup/boot/config.txt`)

```
disable_overscan=0
dtparam=i2c_arm=on
dtparam=spi=on
enable_uart=1
dtoverlay=pi3-miniuart-bt
ignore_lcd=1          # HDMI Eizo primär, 7" DSI aus
lcd_rotate=2          # für späteres Touch-LCD
gpu_mem=128
# start_x=0           # auskommentiert für Desktop
```

### Bewusst NICHT setzen (Geflacker / schwarzer Bildschirm)

| Setting | Problem |
|---------|---------|
| `dtoverlay=vc4-kms-v3d` | KMS instabil auf Pi 3 + Eizo |
| `hdmi_group` / `hdmi_mode` erzwingen | Flackern, falsche Auflösung |
| `hdmi_safe=1` dauerhaft | Nur 640×480, „wackelig“ |
| `framebuffer_width/height` erzwingen | Konflikt mit EDID |
| Desktop-Full-Image blind flashen | LightDM startet nicht zuverlässig |

### Auflösung prüfen (auf dem Pi)

```bash
tvservice -s
# Erwartung: 1280x1024 @ 60Hz (Eizo)
```

### Notfall-Backups auf der SD-Karte

- `/boot/config.txt.bak-640x480` — stabiler Minimalmodus
- `/boot/config.txt.bak-hd-flicker` — dokumentiert fehlgeschlagenen HD-Zwang

## SSH (development PC → Pi)

```
Host raspi
  HostName <PI_IP>
  User pi
  IdentityFile ~/.ssh/id_ed25519
```

Boot partition when flashing: empty file `ssh` + `authorized_keys` (your public key).

After first login: **change the default OS password immediately** (`passwd`). Never commit passwords.

## Apt-Mirror-Fix

Halifax-Mirror war unreachable → IPv4 erzwingen:

`/etc/apt/apt.conf.d/99force-ipv4`:
```
Acquire::ForceIPv4 "true";
```

Sources: offizielle Mirrors (`raspbian.raspberrypi.org`, `archive.raspberrypi.org`).

## GUI-Stack (TempMonitor)

| Paket | Zweck |
|-------|--------|
| python3-kivy 1.11.0 | Touch-UI |
| python3-pyqt5 | PyQtGraph off-screen |
| python3-pyqtgraph | Plot |
| python3-spidev | ADS1118 SPI |
| lightdm + lxde-core | Desktop |

Start TempMonitor:
```bash
~/py/TempMonitor/dev/start_tm_gui.sh
```
(nur **ein** Fenster — Singleton-Lock)

## Neue SD-Karte — Ablauf

1. **Lite-Image** flashen (Etcher), Root-FS expandieren nach erstem Boot
2. Boot-Partition: `ssh`, `authorized_keys`, `config.txt` aus `pi_bullseye_backup/boot/`
3. Pi booten, `ssh raspi`, Passwort setzen
4. Backup-Dateien zurückspielen:
   - `/etc/apt/apt.conf.d/99force-ipv4`
   - `/etc/apt/sources.list` (+ `raspi.list` falls geändert)
   - `/etc/lightdm/lightdm.conf` → `autologin-user=pi`
5. Skripte ausführen:
   ```bash
   bash install_bullseye_gui.sh      # Kivy/PyQt5/spidev
   bash install_bullseye_desktop.sh  # Stretch-ähnlicher Desktop
   ```
6. Projekt nach `/home/pi/py/TempMonitor/dev/` kopieren
7. `tvservice -s` prüfen — **kein** erzwungenes HDMI-Mode setzen
8. `DISPLAY=:0 ~/py/TempMonitor/dev/start_tm_gui.sh`

## Windows-Backups

| Pfad | Inhalt |
|------|--------|
| `pi_bullseye_backup/` | config.txt, apt, lightdm, tarball |
| `pi_stretch_backup/` | alter Stretch-Pi (Referenz) |
| `pi_screenshot_tempmonitor_ok.png` | Erfolgs-Screenshot 2026-07-07 |
| `pi_images/` | Flash-/Recovery-Skripte |

## Desktop aufrüsten (Lite → „richtiger“ Pi-Desktop)

Skript: `install_bullseye_desktop.sh`

Installiert u.a.: **rc-gui** (Pi-Konfiguration), **pipanel**, Panel-Plugins (CPU-Temp, Netzwerk, Lautstärke), **synaptic**, **thonny**, **geany**, **git**, Themes **PiXflat** — **ohne** Chromium/Bloat.

Nach Installation: abmelden/neu anmelden oder Reboot.

## Boot — Dateisystemcheck (Stretch-Stil)

Stretch (`pi_stretch_backup/boot/cmdline.txt`):
```
fsck.repair=yes rootwait rootdelay=5
```
(kein `logo.nologo` → fsck-Fortschritt sichtbar auf HDMI)

Bullseye-Image hatte oft **keinen** periodischen fsck (`tune2fs`: max mount count `-1`, interval `0`).

Skript auf dem Pi:
```bash
sudo bash ~/py/TempMonitor/dev/install_bullseye_boot_fsck.sh
# einmalig fsck beim naechsten Reboot erzwingen:
sudo bash ~/py/TempMonitor/dev/install_bullseye_boot_fsck.sh --force-next-boot
sudo reboot
```

Setzt:
| Einstellung | Wirkung |
|-------------|---------|
| `rootdelay=5` | kurze Pause, Meldungen lesbar |
| ohne `logo.nologo` | kein versteckter Boot-Text |
| `fsck.mode=auto` | prüfen wenn fällig (fstab pass=1) |
| `tune2fs -c 30 -i 6m` | alle 30 Mounts oder 6 Monate |
| fstab `/` pass `1` | root-FS für fsck vorgesehen |

Backup: `pi_bullseye_backup/boot/cmdline.txt`

## 7" Touch-Display (Gen 1.1, DSI)

Umschalten per Terminal (ohne raspi-config-Menü):

```bash
bash ~/py/TempMonitor/dev/set_touch_display.sh status
sudo bash ~/py/TempMonitor/dev/set_touch_display.sh touch   # DSI aktiv
sudo bash ~/py/TempMonitor/dev/set_touch_display.sh hdmi    # Eizo HDMI
sudo reboot
```

| Modus | config.txt | Kivy |
|-------|------------|------|
| **touch** | `#ignore_lcd=1`, `display_default_lcd=1` | `KIVY_BCM_DISPMANX_ID=0` via `~/.config/tm_kivy_display.env` |
| **hdmi** | `ignore_lcd=1`, kein `display_default_lcd` | env-Datei entfernt |

Backup: `/boot/config.txt.bak-pre-touch`  
Details: [`REPORT-kivy-touch-display.md`](REPORT-kivy-touch-display.md)

**Zurueck auf HDMI (Touch):** Desktop-Icon **HDMI (Eizo)** oder in TempMonitor Kivy → Tab **Setup** → Button **HDMI (Eizo)**.

**Auf Touch wechseln (HDMI):** Desktop-Icon **7" Touch-Display** oder Kivy → **Setup** → **7" Touch-Display**.

`start_tm_kivy_gui.sh` startet **nur die Kivy-App** — umschaltet **nicht** das Display. Dafuer die Icons oben verwenden.

Einmalig (oder automatisch bei `set_touch_display.sh touch` / `hdmi`):

```bash
bash ~/py/TempMonitor/dev/install_display_switch_desktop.sh
```

## Bildschirmschoner ohne Passwort

Für Touch-Betrieb (TempMonitor): **keine Passwortabfrage** nach dem Bildschirmschoner.

| Einstellung | Wert |
|-------------|------|
| `~/.config/autostart/light-locker.desktop` | `Hidden=true` (light-locker deaktiviert) |
| `gsettings` | `org.gnome.desktop.screensaver lock-enabled` = **false** |
| `~/.xscreensaver` | `lock: False` |

Backup: `pi_bullseye_backup/home/pi/.config/autostart/light-locker.desktop`  
Nach **Neu-Anmeldung/Reboot** wirksam; aktuelle Session: `light-locker` beendet.

## Was wir von Stretch gelernt haben

- Stretch `config.txt` mit `ignore_lcd=1` + Auto-HDMI = stabil auf Eizo
- Volles Bullseye-Desktop-Image ≠ gleiche Stabilität auf dieser Hardware
- Lite + apt = schneller reproduzierbar als Source-Builds (PyQt/Kivy 3.11)
