# -*- coding: utf-8 -*-
"""CSV sample logger — configurable missing-value token."""

import os
from datetime import datetime

from tm_platform import default_log_dir
from tm_settings import DEFAULT_MISSING_KEY, MISSING_TOKENS

CSV_HEADER = ('Time', 'TC1', 'TC2', 'TC3', 'TC4', 'U1', 'U2')
DEFAULT_LOG_DIR = default_log_dir()


class CsvSampleLogger(object):
    """Append one row per sample; file created when logging is enabled."""

    def __init__(self, log_dir=None):
        self._log_dir = log_dir or DEFAULT_LOG_DIR
        self._fp = None
        self._path = None
        self.enabled = False
        self.missing_key = DEFAULT_MISSING_KEY

    @property
    def path(self):
        return self._path

    def set_missing_key(self, key):
        if key in MISSING_TOKENS:
            self.missing_key = key

    def missing_token(self):
        return MISSING_TOKENS[self.missing_key]

    def start(self):
        if self.enabled:
            return self._path
        os.makedirs(self._log_dir, exist_ok=True)
        fname = datetime.now().strftime('%Y%m%d-%H%M%S') + '.csv'
        self._path = os.path.join(self._log_dir, fname)
        self._fp = open(self._path, 'w', encoding='utf-8', newline='')
        self._fp.write(','.join(CSV_HEADER) + '\n')
        self._fp.flush()
        self.enabled = True
        return self._path

    def stop(self):
        if self._fp:
            self._fp.close()
            self._fp = None
        self.enabled = False

    def write_packet(self, packet, tc_mask, cjc_enabled):
        """
        packet: 6 x (time_s, temp_c|None)
        Disabled UI channels are logged as missing (nan / #N/A / …).
        """
        if not self.enabled or not self._fp or not packet:
            return
        t_sec = packet[0][0]
        cells = [_format_time(t_sec)]
        missing = self.missing_token()
        for i, (_t, temp_c) in enumerate(packet):
            if i < 4:
                if not tc_mask[i]:
                    cells.append(_format_temp(None, missing))
                else:
                    cells.append(_format_temp(temp_c, missing))
            elif not cjc_enabled:
                cells.append(_format_temp(None, missing))
            else:
                cells.append(_format_temp(temp_c, missing))
        self._fp.write(','.join(cells) + '\n')
        self._fp.flush()


def _format_time(t_sec):
    t_sec = float(t_sec)
    if abs(t_sec - round(t_sec)) < 0.05:
        return '{0:.0f}s'.format(t_sec)
    return '{0:.1f}s'.format(t_sec)


def _format_temp(temp_c, missing_token):
    if temp_c is None:
        return missing_token
    return '{0:.1f}\u00b0C'.format(float(temp_c))
