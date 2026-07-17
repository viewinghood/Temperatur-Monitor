# Bullseye Backup — Wiederherstellung

Erstellt: 2026-07-07

## Inhalt

```
boot/
  config.txt              # Aktive HDMI/SPI/I2C-Konfiguration (Stretch-Stil)
  config.txt.bak-*        # Notfall-Kopien von der SD-Karte
  cmdline.txt             # Kernel-Kommandozeile
etc/
  apt/                    # Mirror + IPv4-Fix
  lightdm/lightdm.conf    # Autologin pi
  ssh/                    # (optional) sshd_config aus tarball
bullseye_config_backup.tar.gz   # Gesamtarchiv vom Pi
installed_packages.txt    # Relevante dpkg-Auswahl
```

## Tarball auf neuer SD entpacken (Pi)

```bash
scp pi_bullseye_backup/bullseye_config_backup.tar.gz raspi:/tmp/
ssh raspi
cd /
sudo tar xzf /tmp/bullseye_config_backup.tar.gz
# Pfade im Archiv: boot/, etc/, home/pi/.ssh/
sudo reboot
```

## Einzeldatei config.txt (Windows → Pi Boot-Partition I:)

Vor erstem Boot oder per SSH:
```powershell
scp pi_bullseye_backup\boot\config.txt raspi:/boot/config.txt
```

## Dokumentation

Siehe `BULLSEYE_WORKING_SETUP.md` — Display-Regeln, Geflacker vermeiden, Install-Reihenfolge.
