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
		self.heartbeat_send = 0
		self.heartbeat_recv = 0
		self.heartbeat_online = False
		while self.serial is None:
			try:
				self.serial = serial.Serial(port=self.device, timeout=0.01, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
				print('...opened, waiting for heartbeat...')
				while self.heartbeat_online is False:
					if self.host:
						self.ping()
					self.receive()
					time.sleep(0.1)
			except:
				time.sleep(0.1)
		print("...ready")


	def receive(self):
		line = None
		data = self.serial.readline().decode('utf-8')
		if len(data) > 0:
			line = ""
			while len(data) and '\n' not in data:
				line += data.strip()
				data = self.serial.readline().decode('utf-8')
			line += data.strip()
		if line is not None:
			if len(line) == 0:
				self.heartbeat_recv = time.time()
				if self.host == False:
					self.ping()
				line = None
			else:
				if self.debug:
					if self.host:
						print("USB(D->H): {}".format(line))
					else:
						print("USB(H->D): {}".format(line))
		if (time.time()-self.heartbeat_recv) < 2 and self.heartbeat_online == False:
			self.heartbeat_online = True
		if (time.time()-self.heartbeat_recv) >= 2 and self.heartbeat_online == True:
			self.heartbeat_online = False
		return line


	def ping(self):
		if (time.time()-self.heartbeat_send) > 1:
			self.send("")
			self.heartbeat_send = time.time()


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
			while self.heartbeat_online == True:
				if self.host and time.time()-self.heartbeat_send >= 1:
					self.ping()
				line = self.receive()
				if handler is not None:
					handler(self, line)
			print("Connection closed due to lack of heartbeat")
		except:
			print("Connection closed due to socket error")
#			sys.exit(0)
			raise

