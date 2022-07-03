#!/usr/bin/python3

import serial
import time
import datetime

ser = serial.Serial("/dev/ttyRPI")
ser.baudrate = 115200
ser.bytesize = serial.EIGHTBITS
ser.parity = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_ONE

time.sleep(1)


while True:
	print(ser.readline().decode('utf-8').strip())
	secs = int(datetime.datetime.today().timestamp())
	ser.write(('["time:sync",{"timezone-offset": 2, "epoch-seconds": '+str(secs)+'}]\n').encode('utf-8'))
ser.close()

