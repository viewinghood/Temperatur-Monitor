# -*- coding: utf-8 -*-
# TempMonitor — ADS1118 acquisition (try4)
# Reads all enabled TC channels and optional CJC chip temps each cycle.
# Used by tm_kivy_plot_app.py and optional headless CLI.

import argparse
import sys
import threading
import time

import spidev

from ads1118 import ADS1118, assess_thermocouple_connection, type_k_process_temp


SPI_BUS = 0
SPI_SPEED_HZ = 50000
SPI_MODE = 1

SENSORS = [
    {
        'sensor': 1, 'name': 'TC1', 'adc': 'U1', 'mux': 0,
        'desc': 'U1 AIN0-AIN1', 'invert_polarity': True,
    },
    {
        'sensor': 2, 'name': 'TC2', 'adc': 'U1', 'mux': 1,
        'desc': 'U1 AIN2-AIN3', 'invert_polarity': True,
    },
    {
        'sensor': 3, 'name': 'TC3', 'adc': 'U2', 'mux': 0,
        'desc': 'U2 AIN0-AIN1', 'invert_polarity': True,
    },
    {
        'sensor': 4, 'name': 'TC4', 'adc': 'U2', 'mux': 1,
        'desc': 'U2 AIN2-AIN3', 'invert_polarity': True,
    },
]

ADC_GROUPS = {
    'U1': [s for s in SENSORS if s['adc'] == 'U1'],
    'U2': [s for s in SENSORS if s['adc'] == 'U2'],
}

DEFAULT_ISO_GAIN = 1.0
TC_PGA = ADS1118.PGA_0_256V
TC_SAMPLES = 1
FAST_TRANSFER_S = 0.02
FAST_SETTLE_S = 0.05
CJC_REFRESH_S = 30.0
SAMPLE_INTERVAL_S = 1.0

# Legacy mode constants (CLI)
MODE_TC = 'tc'
MODE_CHIP = 'chip'


def open_spi_devices():
    u1 = spidev.SpiDev()
    u1.open(SPI_BUS, 0)
    u1.max_speed_hz = SPI_SPEED_HZ
    u1.mode = SPI_MODE

    u2 = spidev.SpiDev()
    u2.open(SPI_BUS, 1)
    u2.max_speed_hz = SPI_SPEED_HZ
    u2.mode = SPI_MODE
    return u1, u2


def open_adcs():
    spi_u1, spi_u2 = open_spi_devices()
    adcs = {
        'U1': ADS1118(spi_u1, mux_arr=[ADS1118.MUX_AIN0_AIN1, ADS1118.MUX_AIN2_AIN3]),
        'U2': ADS1118(spi_u2, mux_arr=[ADS1118.MUX_AIN0_AIN1, ADS1118.MUX_AIN2_AIN3]),
    }
    return adcs, spi_u1, spi_u2


class TempMonitorAcquisition(object):
    """Thread-safe reader for multiple TC traces and optional CJC temps."""

    MODE_TC = MODE_TC
    MODE_CHIP = MODE_CHIP

    def __init__(self, iso_gain=DEFAULT_ISO_GAIN):
        self.iso_gain = iso_gain
        self.adcs, self.spi_u1, self.spi_u2 = open_adcs()
        self._lock = threading.Lock()
        self._adc_lock = {'U1': threading.Lock(), 'U2': threading.Lock()}
        self._spi_lock = threading.Lock()
        self._primed = {'U1': False, 'U2': False}
        self._cjc = {'U1': None, 'U2': None}
        self._cjc_t = {'U1': 0.0, 'U2': 0.0}
        self._last_was_adc = {'U1': False, 'U2': False}
        self._tc_enabled = {1}
        self._cjc_enabled = False

    def close(self):
        self.spi_u1.close()
        self.spi_u2.close()

    def set_active(self, tc_sensors, cjc_enabled=False):
        """tc_sensors: iterable of sensor numbers 1..4."""
        with self._lock:
            self._tc_enabled = {
                int(s) for s in tc_sensors if 1 <= int(s) <= 4}
            self._cjc_enabled = bool(cjc_enabled)

    def set_view(self, mode, tc_sensor=1):
        """Legacy single-channel API (headless CLI)."""
        if mode == self.MODE_CHIP:
            self.set_active([], cjc_enabled=True)
        else:
            self.set_active([tc_sensor], cjc_enabled=False)

    def _cjc_for(self, adc_key, force=False):
        with self._adc_lock[adc_key]:
            now = time.time()
            if (force or self._cjc[adc_key] is None
                    or (now - self._cjc_t[adc_key]) > CJC_REFRESH_S):
                with self._spi_lock:
                    adc = self.adcs[adc_key]
                    if self._last_was_adc[adc_key]:
                        for _ in range(2):
                            adc._transfer32(
                                adc.TEMP_CONFIG_MSB, adc.TEMP_CONFIG_LSB, 0.05)
                    temp_c, _, _ = adc.read_chip_temperature(
                        first_delay=0.08, second_delay=0.35)
                self._cjc[adc_key] = temp_c
                self._cjc_t[adc_key] = now
                self._last_was_adc[adc_key] = False
            return self._cjc[adc_key]

    def read_once(self):
        with self._lock:
            tc_enabled = set(self._tc_enabled)
            cjc_enabled = self._cjc_enabled
        return self._read_active_sample(tc_enabled, cjc_enabled)

    def _read_single_tc(self, sensor_def):
        adc_key = sensor_def['adc']
        mux_index = sensor_def['mux']
        with self._adc_lock[adc_key]:
            prime = not self._primed[adc_key]
            self._primed[adc_key] = True

            with self._spi_lock:
                batch = self.adcs[adc_key].read_differential_voltage(
                    mux_index=mux_index,
                    pga=TC_PGA,
                    after_chip_temp=prime,
                    samples=TC_SAMPLES,
                    transfer_delay_s=FAST_TRANSFER_S,
                    settle_s=FAST_SETTLE_S,
                )
            self._last_was_adc[adc_key] = True
        voltages = [item[0] for item in batch]
        raws = [item[1] for item in batch]
        status, detail = assess_thermocouple_connection(voltages, raws)
        mean_v_adc = sum(voltages) / float(len(voltages))
        invert = sensor_def.get('invert_polarity', False)
        mean_v = -mean_v_adc if invert else mean_v_adc

        value = None
        if status == 'connected':
            cjc = self._cjc_for(adc_key)
            value, _, _ = type_k_process_temp(mean_v, cjc, self.iso_gain)

        return {
            'sensor': sensor_def['sensor'],
            'name': sensor_def['name'],
            'adc': adc_key,
            'status': status,
            'detail': detail,
            'value_c': value,
        }

    def _read_adc_group(self, adc_key, tc_enabled, cjc_enabled):
        group = [s for s in ADC_GROUPS[adc_key] if s['sensor'] in tc_enabled]
        if not group and not cjc_enabled:
            return {}, []

        series = {}
        channels = []

        if group and self._cjc[adc_key] is None:
            self._cjc_for(adc_key, force=True)

        for sensor_def in group:
            ch = self._read_single_tc(sensor_def)
            channels.append(ch)
            series[sensor_def['name']] = ch['value_c']

        if group or cjc_enabled:
            self._cjc_for(adc_key, force=True)

        if cjc_enabled and self._cjc[adc_key] is not None:
            series['{0} CJC'.format(adc_key)] = self._cjc[adc_key]
        return series, channels

    def _read_active_sample(self, tc_enabled, cjc_enabled):
        if not tc_enabled and not cjc_enabled:
            return {
                't': time.time(),
                'series': {},
                'channels': [],
                'cjc_enabled': False,
            }

        series = {}
        channels = []
        for adc_key in ('U1', 'U2'):
            group = [s for s in ADC_GROUPS[adc_key] if s['sensor'] in tc_enabled]
            if group or cjc_enabled:
                part_series, part_channels = self._read_adc_group(
                    adc_key, tc_enabled, cjc_enabled)
                series.update(part_series)
                channels.extend(part_channels)

        return {
            't': time.time(),
            'series': series,
            'channels': channels,
            'cjc_enabled': cjc_enabled,
        }


def format_sample_line(sample):
    series = sample.get('series') or {}
    if not series:
        return 'Keine Mess-Spur aktiv — TC1–TC4 oder CJC waehlen'

    parts = []
    for adc_key in ('U1', 'U2'):
        group_parts = []
        for sensor_def in ADC_GROUPS[adc_key]:
            name = sensor_def['name']
            if name not in series:
                continue
            val = series[name]
            if val is not None:
                group_parts.append('{0}={1:.2f}'.format(name, val))
            elif any(ch.get('name') == name for ch in sample.get('channels', [])):
                group_parts.append('{0}=off'.format(name))
            else:
                group_parts.append('{0}=—'.format(name))
        cjc_key = '{0} CJC'.format(adc_key)
        if cjc_key in series and series[cjc_key] is not None:
            group_parts.append('{0}={1:.2f}'.format(cjc_key, series[cjc_key]))
        if group_parts:
            parts.append('{0}: {1}'.format(adc_key, ' '.join(group_parts)))

    return '  |  '.join(parts) if parts else 'Keine Messwerte'


def main():
    parser = argparse.ArgumentParser(
        description='ADS1118 try4 — multi-trace acquisition (headless test)')
    parser.add_argument('--seconds', type=int, default=10, help='run duration')
    parser.add_argument('--mode', choices=('tc', 'chip'), default='tc')
    parser.add_argument('--sensor', type=int, default=1, choices=(1, 2, 3, 4))
    parser.add_argument('--isoGain', type=float, default=DEFAULT_ISO_GAIN)
    args = parser.parse_args()

    acq = TempMonitorAcquisition(iso_gain=args.isoGain)
    acq.set_view(args.mode, args.sensor)
    t_end = time.time() + args.seconds
    n = 0
    try:
        while time.time() < t_end:
            t0 = time.time()
            sample = acq.read_once()
            n += 1
            print('[{0}] {1}'.format(n, format_sample_line(sample)))
            wait = SAMPLE_INTERVAL_S - (time.time() - t0)
            if wait > 0:
                time.sleep(wait)
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        acq.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
