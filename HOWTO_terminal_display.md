# Terminal-Hilfe — Display umschalten (Entwicklung-PC → Pi)

Schnellbefehle vom Entwicklung-PC (PowerShell / Terminal) zum Raspberry Pi.

**Pi:** Host/IP in deiner SSH-Config (`Host raspi`) oder `<PI_IP>` · User: `pi` · Projekt: `~/py/TempMonitor/dev`

---

## Status prüfen

```bash
ssh pi@<PI_IP>
cd ~/py/TempMonitor/dev
bash set_touch_display.sh status
```

---

## Auf 7″ Touch (DSI) umschalten

```bash
ssh pi@<PI_IP>
cd ~/py/TempMonitor/dev
sudo bash set_touch_display.sh touch
sudo reboot
```

Danach **Touch TempMonitor** starten (Desktop-Icon oder Launchbar).

---

## Auf HDMI (Eizo) umschalten

```bash
ssh pi@<PI_IP>
cd ~/py/TempMonitor/dev
sudo bash set_touch_display.sh hdmi
sudo reboot
```

Danach **HDMI TempMonitor** starten.

---

## Einzeiler (ohne interaktive Shell)

**Touch + Reboot:**

```bash
ssh pi@<PI_IP> "cd ~/py/TempMonitor/dev && sudo bash set_touch_display.sh touch && sudo reboot"
```

**HDMI + Reboot:**

```bash
ssh pi@<PI_IP> "cd ~/py/TempMonitor/dev && sudo bash set_touch_display.sh hdmi && sudo reboot"
```

Mit SSH-Config-Alias:

```bash
ssh raspi "cd ~/py/TempMonitor/dev && sudo bash set_touch_display.sh status"
```

---

## Hinweise

| Thema | Detail |
|--------|--------|
| Reboot nötig | Ja — `/boot/config.txt` und Display-Flag werden erst nach Neustart aktiv |
| Alternative | Desktop-Icons **SwitchToTouch** / **SwitchToHDMI** oder App-Einstellungen ☰ |
| Beide schwarz | Mindestens einen Monitor einschalten; im HDMI-Modus ist das DSI-Panel absichtlich aus (`ignore_lcd=1`) |
| Secrets | Keine Passwörter oder privaten Keys in Dateien speichern / committen |
| SSH-Config | siehe `docs/reports/BULLSEYE_WORKING_SETUP.md` |

Mehr Kontext: [README.md](README.md) · [HOWTO_development.md](HOWTO_development.md)
