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

ser.write(('["splash:jpeg",{"filename": "3YVNhnRJA4fODe4IyUIeWN.jpg"}]\n').encode('utf-8'))
while True:
	 print(ser.readline().decode('utf-8').strip())

ser.close()

