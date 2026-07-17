## install raspi hardware
# sudo apt-get install python3-dev python3-rpi.gpio
# https://www.sigmdel.ca/michel/ha/rpi/dnld/draft_spidev_doc.pdf 
# -*- coding: utf-8 -*-
# python3
import spidev
import RPi.GPIO as GPIO
import time
#import socket

#s = socket.socket()
#s.connect(("<PC_IP>", 2222))

GPIO.setmode(GPIO.BOARD)

#~ GPIO.setup(29, GPIO.OUT)
#~ GPIO.setup(31, GPIO.OUT)
#~ GPIO.setup(37, GPIO.OUT)
#~ GPIO.setup(36, GPIO.OUT)

ads1118_u1 = spidev.SpiDev()
ads1118_u1.open(0, 0) # !!CS0 = PIN11
ads1118_u1.max_speed_hz=(50000)
ads1118_u1.mode = 1 # SPI mode = 1

ads1118_u2 = spidev.SpiDev()
ads1118_u2.open(0, 1) # !!CS1 = PIN22
ads1118_u2.max_speed_hz=(50000)
ads1118_u2.mode = 1 # SPI mode = 1

#devices = [ads1118_u1, ads1118_u2]
devices = [ads1118_u2, ads1118_u1]

print("Dev: ", devices)
junctions = [-273.13, -273.13]

CHANNELS = 2

JUNCTION_SCALE = 31.25e-3 # °C/count

#dac = spidev.SpiDev()
#dac.open(0, 0)
#dac.max_speed_hz=(500000)
#dac.mode = 1

#~ slope = [0.935390044, 0.9336188, 0.934022981, 0.92911504, 0.933271588, 0.932049701, 0.937856496, 0.943426834]
#~ offset = [2.303133526, 2.287237477, 3.098093385, 2.504984492, 3.093615643, 2.316805745, 2.984305642, 2.879315687]

#channel = 0

while True:
    for channel, spi_dev in enumerate(devices): #range(0, CHANNELS):
        
        print("ADC U{}".format(channel+1))
        #~ s.send(bytes( str(channel), 'UTF-8'))
        #~ s.send(bytes( ";", 'UTF-8'))
        #~ GPIO.output(29, bool(channel & 0b00000001) )
        #~ GPIO.output(31, bool(channel & 0b00000010) )
        #~ GPIO.output(37, bool(channel & 0b00000100) )
        #~ GPIO.output(36, bool(channel & 0b00001000) )
        
        dout32bit = devices[channel].xfer2([0b10001111, 0b00011011, 0b10001111, 0b00011011])
        time.sleep(0.05)
        # forcing the device to send 2 bytes of data and 2 bytes config register
        # simply repeat the 16-bit device register...
        dout32bit = devices[channel].xfer2([0b10001111, 0b00011011, 0b10001111, 0b00011011])
        #time.sleep(0.1)
        #dout32bit2 = ads1118_u2.xfer2([0b10001111, 0b00011011, 0b10001111, 0b00011011])
        time.sleep(0.5)
        dataMSB = dout32bit[0] 
        dataLSB = dout32bit[1] 
        configMSB = dout32bit[2] 
        configLSB = dout32bit[3]
        
        print( dataMSB,'-',dataLSB,'-',configMSB,'-',configLSB)
        # 14bit data, left justified = 00SMMMMM.MMLLLLLL.LL (M=dataMSB, l=dataLSB)
        # S = sign MSB in dataMSB...
        ads1118_value = (dataMSB << 6) + (dataLSB >> 2)
        print( bin(dataMSB),bin(dataLSB),bin(configMSB),bin(configLSB))
        print( ads1118_value )
        #~ ads1118_value = ads1118_value/16
        #~ voltage = ads1118_value * (4.65455537E-09*16) - (0.000251666817*16) 
        #dout32bit[channel] = ads1118_value*JUNCTION_SCALE
        temp = ads1118_value*JUNCTION_SCALE
        #~ temp = temp * slope[channel] + offset[channel]
        #~ 
        #~ s.send(bytes( str(temp), 'UTF-8'))
        #print( 'U',channel+1,'Chip Temperature Sensor:','{0:.3f}\u00B0C'.format( dout32bit[channel] ))
        print( "U{}".format(channel+1),'Chip Temperature Sensor:','{0:.3f}\u00B0C'.format( temp ))
        #~ 
        #~ s.send(bytes( "\r\n", 'UTF-8'))
        print('=================================================')    
#        time.sleep(0.3)
#        # temperature probe readout ADC=0 in "TS-Mode"
#        dout32bit = devices[channel].xfer([0b10001111, 0b00001011, 0b10001111, 0b00001011])
#        time.sleep(1.5)
#        
#        dataMSB = dout32bit[0] 
#        dataLSB = dout32bit[1] 
#        configMSB = dout32bit[2] 
#        configLSB = dout32bit[3]        
#
#        print( dataMSB,'-',dataLSB,'-',configMSB,'-',configLSB)
#        # 14bit data, left justified = 00SMMMMM.MMLLLLLL.LL (M=dataMSB, l=dataLSB)
#        # S = sign MSB in dataMSB...
#        ads1118_value = (dataMSB << 6) + (dataLSB >> 2)
#        print( bin(dataMSB),bin(dataLSB),bin(configMSB),bin(configLSB))
#        print( ads1118_value )
#        
#        print( 'U',channel+1,'Probe Temperature Sensor:','{0:.3f}\u00B0C'.format( dout32bit[channel] ))
#        #~ 
#        #~ s.send(bytes( "\r\n", 'UTF-8'))
#        print('=================================================')    
#        
ads1118_u1.close()
ads1118_u2.close()
#dac.close()
GPIO.cleanup()

#s.send(bytes( "quit\r\n", 'UTF-8'))
time.sleep(1)
#s.close()



