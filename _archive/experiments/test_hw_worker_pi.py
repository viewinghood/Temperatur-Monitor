#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/pi/py/TempMonitor/dev')

from PyQt5.QtCore import QCoreApplication, QThread, Qt
from tm_hw_worker import TempMonitorHwWorker

app = QCoreApplication([])
worker = TempMonitorHwWorker()
thread = QThread()
worker.moveToThread(thread)
packets = []
errors = []

class Bridge(object):
    @staticmethod
    def on_pkt(p):
        packets.append(p)
    @staticmethod
    def on_err(e):
        errors.append(e)

from PyQt5.QtCore import QObject, pyqtSlot

class R(QObject):
    @pyqtSlot(list)
    def pkt(self, p):
        packets.append(p)
    @pyqtSlot(str)
    def err(self, e):
        errors.append(e)

r = R()
worker.sample_ready.connect(r.pkt, Qt.QueuedConnection)
worker.error.connect(r.err, Qt.QueuedConnection)
thread.started.connect(worker.run)
thread.start()

for _ in range(40):
    app.processEvents()
    import time
    time.sleep(0.1)

worker.stop()
thread.quit()
thread.wait(3000)
print('packets', len(packets))
print('errors', errors)
if packets:
    print('last', packets[-1])
