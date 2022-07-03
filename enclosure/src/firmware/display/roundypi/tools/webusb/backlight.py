#!/usr/bin/python3

import serial
import time

ser = serial.Serial("/dev/ttyRPI")
ser.baudrate = 115200
ser.bytesize = serial.EIGHTBITS
ser.parity = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_ONE

time.sleep(1)

ser.write('["display:backlight", { "action": "set", "status": false } ]\n'.encode('utf-8'))

while True:
	print(ser.readline().decode('utf-8').strip())
ser.close()

