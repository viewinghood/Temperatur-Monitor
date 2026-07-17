# -*- coding: utf-8 -*-
"""
Hardware acquisition worker — QObject in a dedicated QThread.

Emits sample_ready with a fixed list of 6 (time_s, temp_c) pairs:
  index 0..3  → TC1..TC4
  index 4     → U1 CJC
  index 5     → U2 CJC
temp_c is None when the channel is inactive or has no valid reading.
"""

import time

from PyQt5.QtCore import QObject, QMutex, QMutexLocker, pyqtSignal, pyqtSlot

from spi_adc_tm_try4 import SAMPLE_INTERVAL_S, TempMonitorAcquisition
from tm_channels import CHANNEL_NAMES, TC_CHANNEL_INDEX
from tm_status import format_status_line


class TempMonitorHwWorker(QObject):
    """ADS1118 reader; runs its loop inside a QThread (started via run slot)."""

    sample_ready = pyqtSignal(list)
    status_text = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super(TempMonitorHwWorker, self).__init__()
        self._mutex = QMutex()
        self._running = False
        self._tc_enabled = {1}
        self._cjc_enabled = False
        self._tc_mask = [True, False, False, False]
        self._acq = None
        self._t0 = None

    @pyqtSlot()
    def run(self):
        self._running = True
        try:
            self._acq = TempMonitorAcquisition()
        except Exception as exc:
            self.error.emit('SPI/ADC Fehler: {0}'.format(exc))
            self.finished.emit()
            return

        with QMutexLocker(self._mutex):
            self._apply_active_to_hw()

        while self._running:
            loop_start = time.time()
            try:
                with QMutexLocker(self._mutex):
                    sample = self._acq.read_once()
                if sample.get('series') and self._t0 is None:
                    self._t0 = sample['t']
                packet = self._sample_to_packet(sample)
                self.sample_ready.emit(packet)
                with QMutexLocker(self._mutex):
                    tc_mask = list(self._tc_mask)
                    cjc = self._cjc_enabled
                self.status_text.emit(format_status_line(sample, tc_mask, cjc))
            except Exception as exc:
                self.error.emit(str(exc))

            elapsed = time.time() - loop_start
            wait_ms = int(max(0.0, (SAMPLE_INTERVAL_S - elapsed) * 1000.0))
            if wait_ms > 0:
                time.sleep(wait_ms / 1000.0)

        if self._acq:
            self._acq.close()
            self._acq = None
        self.finished.emit()

    @pyqtSlot()
    def stop(self):
        self._running = False

    @pyqtSlot(list, bool)
    def set_active_channels(self, tc_mask, cjc_enabled):
        """tc_mask: list of 4 bool for TC1..TC4."""
        enabled = set()
        for idx, on in enumerate(tc_mask[:4]):
            if on:
                enabled.add(TC_CHANNEL_INDEX[idx])
        with QMutexLocker(self._mutex):
            self._tc_enabled = enabled
            self._tc_mask = [bool(x) for x in tc_mask[:4]]
            self._cjc_enabled = bool(cjc_enabled)
            self._apply_active_to_hw()

    def _apply_active_to_hw(self):
        if self._acq:
            self._acq.set_active(self._tc_enabled, self._cjc_enabled)

    def _sample_to_packet(self, sample):
        series = sample.get('series') or {}
        t_abs = sample.get('t', time.time())
        t_rel = t_abs - self._t0 if self._t0 is not None else 0.0
        packet = []
        for name in CHANNEL_NAMES:
            val = series.get(name)
            if val is None:
                packet.append((t_rel, None))
            else:
                packet.append((t_rel, float(val)))
        return packet
