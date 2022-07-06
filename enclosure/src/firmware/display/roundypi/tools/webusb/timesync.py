#!/usr/bin/python3

import serial
import time
from datetime import datetime, timezone

ser = serial.Serial("/dev/ttyRPI")
ser.baudrate = 115200
ser.bytesize = serial.EIGHTBITS
ser.parity = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_ONE

msg = ""
while "loop()" not in msg:
	msg = ser.readline().decode('utf-8').strip()
	print(msg)

secs = time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds
ser.write(('["time:sync",{"epoch-seconds": '+str(secs)+'}]\n').encode('utf-8'))
while True:
	 print(ser.readline().decode('utf-8').strip())

ser.close()
