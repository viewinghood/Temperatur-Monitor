# -*- coding: utf-8 -*-
# TempMonitor dev test — ADS1118 driver (try3)
# Sequential sensor scanner TC1..TC4; optional internal chip temps at cycle end
#
# Hardware: Raspberry Pi 3, 2x ADS1118 on SPI0 CS0 (U1) and CS1 (U2)

import argparse
import sys
import time

import spidev

from ads1118 import ADS1118, assess_thermocouple_connection, type_k_process_temp


SPI_BUS = 0
SPI_SPEED_HZ = 50000
SPI_MODE = 1

# Scanner order: Sensor 1 .. 4 (MUX stepped per chip)
# PCB wiring: Type K (+) on AIN1 / AIN3; ADS1118 MUX measures AIN0-AIN1 / AIN2-AIN3
# -> software must invert sign (multiply V_adc by -1) for all four sensors.
SENSORS = [
    {
        'sensor': 1, 'name': 'TC1', 'adc': 'U1', 'mux': 0,
        'desc': 'U1 AIN0-AIN1 (Eingang 1, TC+ -> AIN1)', 'expected': 'connected',
        'invert_polarity': True,
    },
    {
        'sensor': 2, 'name': 'TC2', 'adc': 'U1', 'mux': 1,
        'desc': 'U1 AIN2-AIN3 (Eingang 2, TC+ -> AIN3)', 'expected': 'not connected',
        'invert_polarity': True,
    },
    {
        'sensor': 3, 'name': 'TC3', 'adc': 'U2', 'mux': 0,
        'desc': 'U2 AIN0-AIN1 (Eingang 1, TC+ -> AIN1)', 'expected': 'not connected',
        'invert_polarity': True,
    },
    {
        'sensor': 4, 'name': 'TC4', 'adc': 'U2', 'mux': 1,
        'desc': 'U2 AIN2-AIN3 (Eingang 2, TC+ -> AIN3)', 'expected': 'not connected',
        'invert_polarity': True,
    },
]

# TempMonitor PCB: thermocouples via bias resistors directly to ADS1118 diff inputs (no iso amp).
DEFAULT_ISO_GAIN = 1.0
TC_SAMPLES = 8
TC_PGA = ADS1118.PGA_0_256V


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


def mux_label(mux_index):
    if mux_index == 0:
        return 'AIN0-AIN1 (000) differential'
    return 'AIN2-AIN3 (011) differential'


def format_sensor_line(result, chip_temps=None):
    """One-line summary for compact output."""
    label = 'Sensor {0} - {1} ({2})'.format(
        result['sensor'], result['name'], result['adc'])
    if result['status'] == 'connected':
        if chip_temps is not None:
            t_proc = chip_temps[result['adc']] + result['delta_t']
            return '{0}: {1:.2f} C'.format(label, t_proc)
        return '{0}: connected  (delta {1:+.2f} C, add --internalChipTemps for T)'.format(
            label, result['delta_t'])
    if result['status'] == 'not connected':
        return '{0}: not connected'.format(label)
    return '{0}: {1}'.format(label, result['status'])


def scan_sensor(sensor_def, adc, prime_adc, iso_gain=1.0, debug=False):
    """Measure one thermocouple channel (differential voltage only)."""
    mux_index = sensor_def['mux']
    cfg_msb, cfg_lsb = adc.config_bytes(mux_index, pga=TC_PGA, ts_mode=ADS1118.TS_MODE_ADC)
    batch = adc.read_differential_voltage(
        mux_index=mux_index,
        pga=TC_PGA,
        after_chip_temp=prime_adc,
        samples=TC_SAMPLES,
    )
    voltages = [item[0] for item in batch]
    raws = [item[1] for item in batch]
    status, detail = assess_thermocouple_connection(voltages, raws)
    mean_v_adc = sum(voltages) / float(len(voltages))
    mean_raw = int(sum(raws) / float(len(raws)))

    invert = sensor_def.get('invert_polarity', False)
    mean_v = -mean_v_adc if invert else mean_v_adc

    last_rx = batch[-1][4]

    v_tc = mean_v / iso_gain if status == 'connected' else None
    delta_t = None
    if status == 'connected':
        _, _, delta_t = type_k_process_temp(mean_v, 0.0, iso_gain)

    result = {
        'sensor': sensor_def['sensor'],
        'name': sensor_def['name'],
        'desc': sensor_def['desc'],
        'adc': sensor_def['adc'],
        'mux': mux_index,
        'expected': sensor_def['expected'],
        'status': status,
        'detail': detail,
        'mean_v': mean_v,
        'mean_v_adc': mean_v_adc,
        'invert_polarity': invert,
        'mean_raw': mean_raw,
        'v_tc': v_tc,
        'delta_t': delta_t,
        'raws': raws,
        'config': (cfg_msb, cfg_lsb),
        'last_rx': last_rx,
    }

    if debug:
        print('Sensor {0} — {1} ({2})'.format(
            sensor_def['sensor'], sensor_def['name'], sensor_def['desc']))
        print('  ADC: {0}  MUX: {1}'.format(sensor_def['adc'], mux_label(mux_index)))
        print('  config: 0x{0:02X}{1:02X}  PGA=+/-256mV'.format(cfg_msb, cfg_lsb))
        print('  status: {0} ({1})'.format(status, detail))
        print('  V_adc raw: {0:.6f} V ({1:.1f} uV)  raw={2}'.format(
            mean_v_adc, mean_v_adc * 1.0e6, mean_raw))
        if invert:
            print('  polarity: inverted (TC+ on AIN1/AIN3) -> V_tc side {0:.1f} uV'.format(
                mean_v * 1.0e6))
        if status == 'connected':
            gain_note = 'direct' if iso_gain == 1.0 else 'gain {0}'.format(iso_gain)
            print('  V_tc ({1}): {0:.2f} uV'.format(v_tc * 1.0e6, gain_note))
            print('  delta_T (Type K): {0:.3f} C'.format(delta_t))
        else:
            print('  Type K: n/a ({0})'.format(status))
        print('  expected wiring: {0}'.format(sensor_def['expected']))
        print('  samples raw: {0}'.format(raws))
        print('  last SPI: {0}-{1}-{2}-{3}'.format(
            last_rx[0], last_rx[1], last_rx[2], last_rx[3]))

    return result


def print_internal_chip_temps(adcs, debug=False):
    """Optional: internal ADS1118 junction temperatures (not in scan path)."""
    temps = {}
    for label in ('U1', 'U2'):
        temp_c, raw, rx = adcs[label].read_chip_temperature()
        temps[label] = temp_c
        if debug:
            print('{0} internal: {1:.3f} C  (raw={2}, bytes={3}-{4}-{5}-{6})'.format(
                label, temp_c, raw, rx[0], rx[1], rx[2], rx[3]))
    if not debug:
        print('CJC  U1={0:.2f} C  U2={1:.2f} C'.format(temps['U1'], temps['U2']))
    else:
        print('')
        print('--- Internal chip temperatures (CJC reference) ---')
        for label in ('U1', 'U2'):
            print('{0}: {1:.3f} C'.format(label, temps[label]))
    return temps


def print_scan_summary(scan_results, chip_temps=None, debug=False):
    """Compact or verbose per-sensor summary."""
    if debug:
        print('')
        print('--- Summary ---')
    for res in scan_results:
        print(format_sensor_line(res, chip_temps))


def run_cycle(cycle_num, adcs, internal_chip_temps=False, iso_gain=1.0, debug=False):
    if debug:
        print('')
        print('=' * 60)
        print('Cycle {0} — sensor scan (1 -> 2 -> 3 -> 4)'.format(cycle_num))
        print('=' * 60)
    else:
        print('')
        print('Cycle {0}'.format(cycle_num))

    scan_results = []
    primed = {'U1': False, 'U2': False}

    for sensor_def in SENSORS:
        adc_key = sensor_def['adc']
        prime = not primed[adc_key]
        primed[adc_key] = True

        if debug:
            print('-' * 40)
        result = scan_sensor(
            sensor_def, adcs[adc_key], prime_adc=prime, iso_gain=iso_gain, debug=debug)
        scan_results.append(result)

    if internal_chip_temps:
        chip_temps = print_internal_chip_temps(adcs, debug=debug)
        print_scan_summary(scan_results, chip_temps, debug=debug)
    else:
        print_scan_summary(scan_results, debug=debug)


def main():
    parser = argparse.ArgumentParser(description='ADS1118 TempMonitor try3 scanner')
    parser.add_argument('--cycles', type=int, default=5, help='scan cycles (default 5)')
    parser.add_argument('--interval', type=float, default=1.0, help='pause between cycles (s)')
    parser.add_argument('--debug', action='store_true', help='print raw sample arrays')
    parser.add_argument(
        '--internalChipTemps', action='store_true',
        help='measure U1/U2 internal chip temperature at end of each cycle (CJC)',
    )
    parser.add_argument(
        '--isoGain', type=float, default=DEFAULT_ISO_GAIN,
        help='external amp gain between TC and ADC (default 1.0 = direct connection)',
    )
    args = parser.parse_args()

    if args.debug:
        print('TempMonitor ADS1118 try3 — sequential scanner')
        print('SPI: bus={0} speed={1} Hz  cycles={2}  internalChipTemps={3}'.format(
            SPI_BUS, SPI_SPEED_HZ, args.cycles, args.internalChipTemps))

    spi_u1, spi_u2 = open_spi_devices()
    adcs = {
        'U1': ADS1118(spi_u1, mux_arr=[ADS1118.MUX_AIN0_AIN1, ADS1118.MUX_AIN2_AIN3]),
        'U2': ADS1118(spi_u2, mux_arr=[ADS1118.MUX_AIN0_AIN1, ADS1118.MUX_AIN2_AIN3]),
    }

    try:
        for i in range(1, args.cycles + 1):
            run_cycle(
                i, adcs, internal_chip_temps=args.internalChipTemps,
                iso_gain=args.isoGain, debug=args.debug)
            if i < args.cycles:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print('\nStopped by user.')
    finally:
        spi_u1.close()
        spi_u2.close()

    print('')
    print('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
