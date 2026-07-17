# -*- coding: utf-8 -*-
"""App settings — CSV missing-value tokens and plot time window."""

MISSING_NAN = 'nan'
MISSING_NA = 'na'
MISSING_EXCEL = 'excel'
MISSING_NULL = 'null'

MISSING_TOKENS = {
    MISSING_NAN: 'nan',
    MISSING_NA: '#N/A',
    MISSING_EXCEL: '',
    MISSING_NULL: 'null',
}

MISSING_LABELS = (
    (MISSING_NAN, 'nan (Igor)'),
    (MISSING_NA, '#N/A (Excel Diagram)'),
    (MISSING_EXCEL, ',, (leer Excel)'),
    (MISSING_NULL, 'null (Python / SQL)'),
)

DEFAULT_MISSING_KEY = MISSING_NAN

PLOT_WINDOW_ALL = 'all'
PLOT_WINDOW_1M = '1m'
PLOT_WINDOW_10M = '10m'
PLOT_WINDOW_1H = '1h'
PLOT_WINDOW_12H = '12h'
PLOT_WINDOW_1D = '1d'

PLOT_WINDOW_SECONDS = {
    PLOT_WINDOW_ALL: None,
    PLOT_WINDOW_1M: 60,
    PLOT_WINDOW_10M: 600,
    PLOT_WINDOW_1H: 3600,
    PLOT_WINDOW_12H: 43200,
    PLOT_WINDOW_1D: 86400,
}

PLOT_WINDOW_LABELS = (
    (PLOT_WINDOW_ALL, 'Alles (0 bis Ende)'),
    (PLOT_WINDOW_1M, '1 Minute'),
    (PLOT_WINDOW_10M, '10 Minuten'),
    (PLOT_WINDOW_1H, '1 Stunde'),
    (PLOT_WINDOW_12H, '12 Stunden'),
    (PLOT_WINDOW_1D, '1 Tag'),
)

DEFAULT_PLOT_WINDOW_KEY = PLOT_WINDOW_ALL


def plot_window_seconds(key):
    """None = show full history from t=0."""
    return PLOT_WINDOW_SECONDS.get(key, None)
n 