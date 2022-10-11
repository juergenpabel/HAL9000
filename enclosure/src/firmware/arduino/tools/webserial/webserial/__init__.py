#!/usr/bin/python3

import sys
import serial
import time


class webserial:
	def __init__(self, device: str = None):
		self.device = device
		if self.device is None:
			self.device = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyRP2040"

	def connect(self):
		print("Connecting to {}...".format(self.device))
		self.serial = None
		while self.serial is None:
			try:
				self.serial = serial.Serial(port=self.device, timeout=1, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
			except:
				time.sleep(0.1)
		print("Connected")
		self.send('run')
		line = self.receive()
		while "loop()" not in line:
			line = self.receive()


	def receive(self):
		line = ""
		data = self.serial.readline().decode('utf-8')
		while len(data) and '\n' not in data:
			line += data
			data = self.serial.readline().decode('utf-8')
		line += data.strip()
		if len(line):
			print("USB(D->H): {}".format(line))
		return line


	def send(self, line: str):
		print("USB(H->D): {}".format(line))
		if not line.endswith("\n"):
			line += "\n"
		self.serial.write(line.encode('utf-8'))


	def run(self, handler=None):
		try:
			while True:
				line = self.receive()
				if handler is not None:
					handler(self, line)
		except:
			print("Connection closed")
			sys.exit(0)



