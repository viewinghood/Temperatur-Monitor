# -*- coding: utf-8 -*-
"""One-time Pi SSH key install — credentials via environment only.

Example (PowerShell):
  $env:TM_PI_HOST = '192.168.x.x'
  $env:TM_PI_USER = 'pi'
  $env:TM_PI_PASS = '<your-password>'   # do not commit
  python pi_setup_once.py
"""
import os
import pathlib
import sys

try:
    import paramiko
except ImportError:
    print('Install paramiko first: pip install paramiko', file=sys.stderr)
    sys.exit(1)

PUB_PATH = os.environ.get(
    'TM_SSH_PUBKEY',
    os.path.join(os.path.expanduser('~'), '.ssh', 'id_ed25519.pub'))
HOST = os.environ.get('TM_PI_HOST')
USER = os.environ.get('TM_PI_USER', 'pi')
PASS = os.environ.get('TM_PI_PASS')

if not HOST or not PASS:
    print(
        'Set TM_PI_HOST and TM_PI_PASS in the environment. '
        'Never hard-code passwords in this file.',
        file=sys.stderr)
    sys.exit(1)

pub_file = pathlib.Path(PUB_PATH)
if not pub_file.is_file():
    print('Public key not found: {0}'.format(PUB_PATH), file=sys.stderr)
    sys.exit(1)

PUB = pub_file.read_text(encoding='utf-8').strip()

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    HOST, username=USER, password=PASS, timeout=20,
    allow_agent=False, look_for_keys=False)


def run(cmd):
    _, o, e = c.exec_command(cmd)
    return (o.read() + e.read()).decode('utf-8', errors='replace')


print('=== SYSTEM ===')
print(run('uname -a; cat /etc/os-release | head -3; systemctl is-system-running'))
print('=== HARDWARE ===')
print(run('ls -l /dev/spidev* /dev/i2c* 2>&1'))
print('=== SSH KEY ===')
token = PUB.split()[1]
print(
    run(
        'mkdir -p ~/.ssh && chmod 700 ~/.ssh && '
        'grep -qF "{0}" ~/.ssh/authorized_keys 2>/dev/null || '
        'echo "{1}" >> ~/.ssh/authorized_keys && '
        'chmod 600 ~/.ssh/authorized_keys && echo KEY_OK'.format(token, PUB)
    )
)
c.close()
print('DONE')
