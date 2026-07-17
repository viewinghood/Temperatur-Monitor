# -*- coding: utf-8 -*-
"""Quick diagnostic: compare U1/U2 CJC and TC3/TC4 raw readings."""
import time

from spi_adc_tm_try4 import TempMonitorAcquisition

acq = TempMonitorAcquisition()
acq.set_active([3, 4], cjc_enabled=True)
print('CJC cache:', acq._cjc)
for i in range(8):
    s = acq.read_once()
    ser = s.get('series') or {}
    print('--- sample {0}'.format(i + 1))
    print('  U1 CJC: {0}'.format(ser.get('U1 CJC')))
    print('  U2 CJC: {0}'.format(ser.get('U2 CJC')))
    print('  cache U1={0} U2={1}'.format(acq._cjc['U1'], acq._cjc['U2']))
    print('  cache t U1={0:.1f} U2={1:.1f}'.format(
        acq._cjc_t['U1'], acq._cjc_t['U2']))
    for ch in s.get('channels') or []:
        print('  {0}: status={1} value={2} | {3}'.format(
            ch['name'], ch['status'], ch.get('value_c'), ch.get('detail')))
    time.sleep(1)
acq.close()
