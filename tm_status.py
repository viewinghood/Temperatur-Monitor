# -*- coding: utf-8 -*-
"""Status line formatting for TempMonitor UI."""

from tm_channels import CHANNEL_NAMES


def format_status_line(sample, tc_mask, cjc_enabled):
    """
    Example: TC1=28.76°C  TC2 OFF  |  U1(CJC)=30.2°C  U2(CJC)=30.0°C
    Only enabled channels are listed.
    """
    series = sample.get('series') or {}
    if not any(tc_mask) and not cjc_enabled:
        return 'Keine Spur aktiv — TC1–TC4 oder CJC waehlen'

    parts = []
    for i, name in enumerate(CHANNEL_NAMES[:4]):
        if not tc_mask[i]:
            continue
        val = series.get(name)
        if val is not None:
            parts.append('{0}={1:.2f}\u00b0C'.format(name, val))
        else:
            parts.append('{0} OFF'.format(name))

    if cjc_enabled:
        for adc_key, label in (('U1', 'U1(CJC)'), ('U2', 'U2(CJC)')):
            key = '{0} CJC'.format(adc_key)
            val = series.get(key)
            if val is not None:
                parts.append('{0}={1:.2f}\u00b0C'.format(label, val))
            else:
                parts.append('{0} OFF'.format(label))

    if not parts:
        return 'Keine Messwerte'
    return '   '.join(parts)
