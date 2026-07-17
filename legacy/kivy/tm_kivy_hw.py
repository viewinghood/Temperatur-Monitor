# -*- coding: utf-8 -*-
"""Hardware polling for Kivy — plain thread + queue (no Qt signals)."""

import queue
import threading
import time

from spi_adc_tm_try4 import SAMPLE_INTERVAL_S, TempMonitorAcquisition
from tm_channels import CHANNEL_NAMES, TC_CHANNEL_INDEX
from tm_status import format_status_line


class KivyHwPoller:
    """Background SPI reader; main thread calls poll_one()."""

    def __init__(self):
        self._q = queue.Queue()
        self._lock = threading.Lock()
        self._latest_sample = None
        self._running = False
        self._thread = None
        self._tc_mask = [True, False, False, False]
        self._cjc = False
        self._t0 = None
        self._acq = None

    def set_active_channels(self, tc_mask, cjc_enabled):
        enabled = set()
        for idx, on in enumerate(tc_mask[:4]):
            if on:
                enabled.add(TC_CHANNEL_INDEX[idx])
        with self._lock:
            self._tc_mask = [bool(x) for x in tc_mask[:4]]
            self._cjc = bool(cjc_enabled)
            if self._acq is not None:
                self._acq.set_active(enabled, self._cjc)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name='tm_kivy_hw', daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=4.0)
            self._thread = None

    def poll_one(self):
        """Return one event or None (errors first, then latest sample)."""
        try:
            return self._q.get_nowait()
        except queue.Empty:
            pass
        with self._lock:
            if self._latest_sample is not None:
                item = self._latest_sample
                self._latest_sample = None
                return item
        return None

    def poll(self):
        """Return all pending events (legacy)."""
        items = []
        while True:
            item = self.poll_one()
            if item is None:
                break
            items.append(item)
        return items

    def _enqueue(self, item):
        if item[0] == 'sample':
            with self._lock:
                self._latest_sample = item
            return
        try:
            self._q.put_nowait(item)
        except queue.Full:
            pass

    def _loop(self):
        try:
            self._acq = TempMonitorAcquisition()
        except Exception as exc:
            self._enqueue(('error', 'SPI/ADC Fehler: {0}'.format(exc)))
            self._running = False
            return

        with self._lock:
            enabled = {TC_CHANNEL_INDEX[i] for i, on in enumerate(self._tc_mask) if on}
            self._acq.set_active(enabled, self._cjc)

        while self._running:
            loop_start = time.time()
            try:
                with self._lock:
                    tc_mask = list(self._tc_mask)
                    cjc = self._cjc
                sample = self._acq.read_once()
                if sample.get('series') and self._t0 is None:
                    self._t0 = sample['t']
                packet = self._sample_to_packet(sample)
                status = format_status_line(sample, tc_mask, cjc)
                self._enqueue(('sample', packet, status))
            except Exception as exc:
                self._enqueue(('error', str(exc)))

            elapsed = time.time() - loop_start
            wait = SAMPLE_INTERVAL_S - elapsed
            if wait > 0:
                time.sleep(wait)

        if self._acq is not None:
            self._acq.close()
            self._acq = None

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
