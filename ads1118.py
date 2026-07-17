# -*- coding: utf-8 -*-
# ADS1118 Python3 driver for Raspberry Pi (spidev)
# Ported from MicroPython driver by Richard Heming:
# https://github.com/viewinghood/ads1118
# License: MIT

import time
import struct


class ADS1118(object):
    """Driver for TI ADS1118 16-bit ADC with integrated temperature sensor."""

    MUX_AIN0_AIN1 = '000'
    MUX_AIN0_AIN3 = '001'
    MUX_AIN1_AIN3 = '010'
    MUX_AIN2_AIN3 = '011'
    MUX_AIN0 = '100'
    MUX_AIN1 = '101'
    MUX_AIN2 = '110'
    MUX_AIN3 = '111'

    PGA_6_144V = '000'
    PGA_4_096V = '001'
    PGA_2_048V = '010'
    PGA_1_024V = '011'
    PGA_0_512V = '100'
    PGA_0_256V = '111'

    MODE_CONTINUOUS = '0'
    MODE_SINGLESHOT = '1'

    DATARATE_8_SPS = '000'
    DATARATE_16_SPS = '001'
    DATARATE_32_SPS = '010'
    DATARATE_64_SPS = '011'
    DATARATE_128_SPS = '100'
    DATARATE_250_SPS = '101'
    DATARATE_475_SPS = '110'
    DATARATE_860_SPS = '111'

    TS_MODE_ADC = '0'
    TS_MODE_TEMP = '1'

    SCALE_6_144V = '000'
    SCALE_4_096V = '001'
    SCALE_2_048V = '010'
    SCALE_1_024V = '011'
    SCALE_0_512V = '100'
    SCALE_0_256V = '111'

    ADC_CONVERSION_FACTORS = {
        PGA_6_144V: 6.144 / 32767.0,
        PGA_4_096V: 4.096 / 32767.0,
        PGA_2_048V: 2.048 / 32767.0,
        PGA_1_024V: 1.024 / 32767.0,
        PGA_0_512V: 0.512 / 32767.0,
        PGA_0_256V: 0.256 / 32767.0,
    }

    ADC_SCALING_FACTORS = {
        SCALE_6_144V: 6114,
        SCALE_4_096V: 4096,
        SCALE_2_048V: 2048,
        SCALE_1_024V: 1024,
        SCALE_0_512V: 512,
        SCALE_0_256V: 256,
    }

    TEMP_CONFIG_MSB = 0x8F
    TEMP_CONFIG_LSB = 0x1B
    TEMP_SCALE_C_PER_COUNT = 31.25e-3

    def __init__(self, spi_dev, mux_arr=None, default_pga=PGA_2_048V):
        """
        :param spi_dev: opened spidev.SpiDev instance (CS handled by spidev)
        :param mux_arr: list of MUX constants for each channel index
        """
        self.spi = spi_dev
        if mux_arr is None:
            mux_arr = [self.MUX_AIN0_AIN1, self.MUX_AIN2_AIN3]
        self.mux_arr = mux_arr
        self.default_pga = default_pga
        self.commands = []
        for mux in mux_arr:
            self.commands.append(
                self._encode_command(mux=mux, pga=default_pga, ts_mode=self.TS_MODE_ADC)
            )

    def _encode_command(
        self,
        start_single_shot=False,
        mux=MUX_AIN0_AIN1,
        pga=PGA_2_048V,
        mode=MODE_CONTINUOUS,
        datarate=DATARATE_128_SPS,
        ts_mode=TS_MODE_ADC,
        pullup_enable=True,
        nop_valid=True,
    ):
        output_s = '1' if start_single_shot else '0'
        output_s += str(mux)
        output_s += str(pga)
        output_s += str(mode)
        output_s += str(datarate)
        output_s += str(ts_mode)
        output_s += '1' if pullup_enable else '0'
        output_s += '01' if nop_valid else '00'
        output_s += '1'
        return bytearray([int(output_s[:8], 2), int(output_s[8:], 2)])

    def _transfer32(self, msb, lsb, delay_s=0.05):
        """32-bit SPI frame: config word sent twice (Raspberry Pi / try2 style)."""
        frame = [msb, lsb, msb, lsb]
        self.spi.xfer2(frame)
        time.sleep(delay_s)
        return self.spi.xfer2(frame)

    @staticmethod
    def _parse_chip_temp_from_bytes(data_msb, data_lsb):
        """Decode internal temperature (try2 / datasheet left-justified 14-bit)."""
        raw = (data_msb << 6) + (data_lsb >> 2)
        if data_msb & 0x80:
            raw -= 16384
        return raw * ADS1118.TEMP_SCALE_C_PER_COUNT, raw

    @staticmethod
    def _parse_adc_raw(data_msb, data_lsb):
        value = (data_msb << 8) + data_lsb
        if value >= 0x8000:
            value -= 0x10000
        return value

    def config_bytes(self, mux_index=0, pga=None, ts_mode=TS_MODE_ADC, start_single_shot=False):
        """Return 16-bit config register for a MUX channel (for debug)."""
        if pga is None:
            pga = self.default_pga
        cmd = self._encode_command(
            mux=self.mux_arr[mux_index],
            pga=pga,
            ts_mode=ts_mode,
            start_single_shot=start_single_shot,
        )
        return cmd[0], cmd[1]

    def _adc_config(self, mux_index=0, pga=None, single_shot=True):
        if pga is None:
            pga = self.default_pga
        mode = self.MODE_SINGLESHOT if single_shot else self.MODE_CONTINUOUS
        return self._encode_command(
            start_single_shot=single_shot,
            mux=self.mux_arr[mux_index],
            pga=pga,
            mode=mode,
            ts_mode=self.TS_MODE_ADC,
        )

    def _switch_to_adc_mode(self, mux_index=0, pga=None):
        """
        Leave chip-temperature mode and prime the ADC for differential reading.
        Mirrors MicroPython driver: config write + discard after TS_MODE.
        """
        cmd = self._adc_config(mux_index, pga=pga)
        self._transfer32(cmd[0], cmd[1], 0.05)
        time.sleep(0.05)
        self._transfer32(cmd[0], cmd[1], 0.05)
        time.sleep(0.12)

    def read_chip_temperature(self, first_delay=0.05, second_delay=0.5):
        """
        Read ADS1118 die (junction) temperature in degrees Celsius.
        Three 32-bit transfers: discard stale data after ADC mode, then read.
        """
        self._transfer32(self.TEMP_CONFIG_MSB, self.TEMP_CONFIG_LSB, 0.05)
        self._transfer32(self.TEMP_CONFIG_MSB, self.TEMP_CONFIG_LSB, first_delay)
        rx = self._transfer32(self.TEMP_CONFIG_MSB, self.TEMP_CONFIG_LSB, second_delay)
        temp_c, raw = self._parse_chip_temp_from_bytes(rx[0], rx[1])
        return temp_c, raw, rx

    def read_differential_voltage(
        self,
        mux_index=0,
        pga=None,
        after_chip_temp=False,
        samples=1,
        transfer_delay_s=0.05,
        settle_s=0.12,
    ):
        """
        Read MUX differential voltage (e.g. AIN0-AIN1 for mux_index=0, MUX='000').

        ADS1118 MUX 000 = AIN0 positive, AIN1 negative (datasheet Table 8-1).
        Returns list of (v_adc_v, raw, config_msb, config_lsb, rx) per sample.
        """
        if pga is None:
            pga = self.default_pga
        if after_chip_temp:
            self._switch_to_adc_mode(mux_index, pga=pga)

        cmd = self._adc_config(mux_index, pga=pga)
        results = []
        for _ in range(samples):
            self._transfer32(cmd[0], cmd[1], transfer_delay_s)
            time.sleep(settle_s)
            rx = self._transfer32(cmd[0], cmd[1], transfer_delay_s)
            raw = self._parse_adc_raw(rx[0], rx[1])
            voltage = raw * self.ADC_CONVERSION_FACTORS[pga]
            results.append((voltage, raw, rx[0], rx[1], rx))
        return results

    def read_voltage(self, mux_index=0, pga=None, settle_s=0.05, samples=1, after_chip_temp=False):
        """
        Read differential/single-ended voltage for preconfigured mux index.
        Returns (voltage_v, raw, pga_key) or lists if samples>1.
        """
        batch = self.read_differential_voltage(
            mux_index=mux_index,
            pga=pga,
            after_chip_temp=after_chip_temp,
            samples=samples,
        )
        voltages = [item[0] for item in batch]
        raw_values = [item[1] for item in batch]
        pga_key = pga if pga is not None else self.default_pga
        if samples == 1:
            return voltages[0], raw_values[0], pga_key
        return voltages, raw_values, pga_key

    def read_data(self, mux_index=0, ts_mode=TS_MODE_ADC, pga=None, scale=SCALE_2_048V, samples=1):
        """
        MicroPython-compatible API wrapper.
        ts_mode='1' -> chip temperature; '0' -> ADC voltage.
        """
        if ts_mode == self.TS_MODE_TEMP:
            temp_c, raw, rx = self.read_chip_temperature()
            return temp_c, raw, self.ADC_SCALING_FACTORS[scale]
        voltage, raw, pga_key = self.read_voltage(mux_index=mux_index, pga=pga, samples=samples)
        if samples == 1:
            return voltage, raw, self.ADC_SCALING_FACTORS[scale]
        return voltage, raw, self.ADC_SCALING_FACTORS[scale]


def type_k_delta_c_from_voltage(v_tc_volts):
    """
    Type K inverse (IEC 60584 / NIST ITS-90), voltage in VOLTS at thermocouple.
    Returns equivalent temperature rise above cold junction (°C) for small signals.
    Polynomial valid for 0 .. 20.644 mV (positive).
    """
    mv = v_tc_volts * 1000.0
    if mv >= 0.0:
        return (
            -3.1840969275e-12 * mv ** 8
            + 2.1623681444e-8 * mv ** 7
            - 5.8090870727e-5 * mv ** 6
            + 7.2099740664e-2 * mv ** 5
            - 4.7348932413e-2 * mv ** 4
            + 1.0589699170e-1 * mv ** 3
            + 1.2080523380e-2 * mv ** 2
            + 2.5173461291e1 * mv
        )
    mv = -mv
    return -(
        -3.1840969275e-12 * mv ** 8
        + 2.1623681444e-8 * mv ** 7
        - 5.8090870727e-5 * mv ** 6
        + 7.2099740664e-2 * mv ** 5
        - 4.7348932413e-2 * mv ** 4
        + 1.0589699170e-1 * mv ** 3
        + 1.2080523380e-2 * mv ** 2
        + 2.5173461291e1 * mv
    )


def type_k_process_temp(v_adc_volts, cold_junction_c, iso_amp_gain=1.0):
    """
    Convert amplified ADC differential voltage to process temperature with CJC.

    Signal chain (TempMonitor PCB):
      V_tc at thermocouple -> bias resistors -> ADS1118 diff input (gain=1)
      With external amplifier: V_adc = gain * V_tc
    """
    v_tc = v_adc_volts / iso_amp_gain
    delta_t = type_k_delta_c_from_voltage(v_tc)
    return cold_junction_c + delta_t, v_tc, delta_t


def assess_thermocouple_connection(
    voltages,
    raws,
    saturation_raw=30000,
    open_offset_v=0.010,
    connected_max_raw=200,
):
    """
    Heuristic: connected vs open/floating thermocouple input.
    Returns (status, detail_string).

    On this PCB, unconnected differential inputs float to ~+320 mV or ~-170 mV
    bias (observed on TC2-TC4). A connected Type K at room temperature shows
    near-zero differential voltage (raw typically < 20).
    """
    if not voltages:
        return 'unknown', 'no samples'
    v_min = min(voltages)
    v_max = max(voltages)
    span = v_max - v_min
    mean_v = sum(voltages) / float(len(voltages))
    max_abs_raw = max(abs(r) for r in raws)
    abs_mean_v = abs(mean_v)

    if max_abs_raw >= saturation_raw:
        return 'open/fault', 'ADC near saturation (|raw|>={0})'.format(saturation_raw)
    if abs_mean_v >= open_offset_v:
        return 'not connected', 'floating bias {0:.1f} mV (|mean|>={1:.0f} mV)'.format(
            mean_v * 1000.0, open_offset_v * 1000.0)
    if max_abs_raw <= connected_max_raw:
        return 'connected', 'near CJC equilibrium (raw<={0}, span={1:.3f} mV)'.format(
            connected_max_raw, span * 1000.0)
    return 'connected', 'signal span={0:.3f} mV mean={1:.3f} mV raw_max={2}'.format(
        span * 1000.0, mean_v * 1000.0, max_abs_raw)
