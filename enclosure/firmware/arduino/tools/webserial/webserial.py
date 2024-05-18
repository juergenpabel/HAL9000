#!/usr/bin/python3

import sys
import serial
import time


class webserial:

	def __init__(self, host: bool = False, debug: bool = True):
		self.device = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyHAL9000"
		self.host = host
		self.debug = debug


	def reset(self):
		print(f"Resetting '{self.device}' via RTS...")
		hal9000 = serial.Serial(port=self.device, timeout=1, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
		hal9000.setRTS(True)
		time.sleep(0.1)
		hal9000.setRTS(False)
		time.sleep(0.1)
		hal9000.close()
		

	def connect(self):
		print("Connecting to '{}' (host={})...".format(self.device, self.host))
		self.serial = None
		while self.serial is None:
			try:
				self.serial = serial.Serial(port=self.device, timeout=0.01, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
			except:
				time.sleep(0.1)
		print("...ready")
		self.send('["application/runtime", {"status":"?"}]')


	def receive(self):
		line = None
		data = self.serial.readline().decode('utf-8')
		if len(data) > 0:
			line = ""
			while len(data) and '\n' not in data:
				line += data.strip()
				try:
					data = self.serial.readline()
					data = data.decode('utf-8')
				except:
					print(data)
					data = ""
			line += data.strip()
		if line is not None:
			if self.debug:
				if self.host:
					print("USB(D->H): {}".format(line))
				else:
					print("USB(H->D): {}".format(line))
		return line


	def send(self, line: str):
		if self.debug and len(line) > 0:
			if self.host:
				print("USB(H->D): {}".format(line))
			else:
				print("USB(D->H): {}".format(line))
		if not line.endswith("\n"):
			line += "\n"
		self.serial.write(line.encode('utf-8'))
		self.serial.flush()


	def run(self, handler=None):
		try:
			while True:
				line = self.receive()
				if handler is not None:
					handler(self, line)
		except:
			print("Connection closed due to socket error")
#			sys.exit(0)
			raise

