# -*- coding: utf-8 -*-
"""Channel definitions shared by hardware worker and PyQt UI."""

CHANNEL_NAMES = ('TC1', 'TC2', 'TC3', 'TC4', 'U1 CJC', 'U2 CJC')
NUM_CHANNELS = 6

# UI / plot colours — U1 pair blue, U2 pair green, CJC orange.
CHANNEL_COLORS = {
    'TC1': '#4fc3f7',
    'TC2': '#0288d1',
    'TC3': '#81c784',
    'TC4': '#388e3c',
    'U1 CJC': '#ffb74d',
    'U2 CJC': '#f57c00',
}

# TC1..TC4 map to acquisition sensor numbers 1..4.
TC_CHANNEL_INDEX = {0: 1, 1: 2, 2: 3, 3: 4}

MAX_HISTORY = 90000
