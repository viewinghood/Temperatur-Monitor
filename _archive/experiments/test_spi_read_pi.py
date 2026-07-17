#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/pi/py/TempMonitor/dev')
from spi_adc_tm_try4 import TempMonitorAcquisition
a = TempMonitorAcquisition()
s = a.read_once()
print('sample:', s)
a.close()
