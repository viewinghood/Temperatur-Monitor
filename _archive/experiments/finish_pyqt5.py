#!/usr/bin/env python3
"""Non-interactive sip-install (answers GPL license prompt)."""
import os
import pexpect
import sys

os.environ["PATH"] = (
    "/home/pi/local/python311/bin:/home/pi/local/qt515/bin:"
    + os.environ.get("PATH", "")
)
os.environ["LD_LIBRARY_PATH"] = (
    "/home/pi/local/openssl111/lib:"
    + os.environ.get("LD_LIBRARY_PATH", "")
)
os.environ["QMAKE"] = "/home/pi/local/qt515/bin/qmake"

child = pexpect.spawn(
    "sip-install",
    cwd="/tmp/PyQt5-5.15.11",
    timeout=7200,
    encoding="utf-8",
)
child.logfile = sys.stdout
while True:
    i = child.expect(
        ["Do you accept the terms of the license\\?", pexpect.EOF, pexpect.TIMEOUT]
    )
    if i == 0:
        child.sendline("yes")
    elif i == 1:
        break
    else:
        sys.exit("TIMEOUT waiting for sip-install")
code = child.wait()
sys.exit(code)
