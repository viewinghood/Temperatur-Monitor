#!/usr/bin/env python3
"""Fix HDMI flicker: Stretch-style auto EDID (no forced mode).

Set TM_PI_HOST (and optional TM_PI_USER) in the environment. Uses SSH keys.
"""
import os
import paramiko

CONFIG = r"""# TempMonitor — Stretch-style HDMI (auto EDID, Eizo 1280x1024)
# NO forced hdmi_group/mode — let monitor negotiate like Stretch

disable_overscan=0

dtparam=i2c_arm=on
dtparam=spi=on
dtparam=audio=on
enable_uart=1
dtoverlay=pi3-miniuart-bt

ignore_lcd=1
lcd_rotate=2

start_x=0
gpu_mem=128
camera_auto_detect=0
display_auto_detect=0

[all]
"""

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    os.environ.get('TM_PI_HOST', '127.0.0.1'),
    username=os.environ.get('TM_PI_USER', 'pi'),
    timeout=15,
    allow_agent=True,
    look_for_keys=True,
)

def run(cmd):
    _, o, e = c.exec_command(cmd)
    return (o.read() + e.read()).decode()

print(run("sudo cp /boot/config.txt /boot/config.txt.bak-hd-flicker"))
# write config
sftp = c.open_sftp()
with sftp.file("/tmp/config.txt.new", "w") as f:
    f.write(CONFIG)
sftp.close()
print(run("sudo cp /tmp/config.txt.new /boot/config.txt && grep -E 'hdmi|ignore|lcd|overscan' /boot/config.txt"))
print("Rebooting...")
c.exec_command("sudo reboot")
c.close()
print("Done — wait 50s then check tvservice")
