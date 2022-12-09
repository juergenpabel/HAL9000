#!/usr/bin/env python3

import logging
import time
import serial
from configparser import ConfigParser

from . import HAL9000_Driver


class Driver(HAL9000_Driver):

	def __init__(self, name: str):
		HAL9000_Driver.__init__(self, name)
		self.config = dict()
		if hasattr(Driver, 'serial') is False:
			Driver.serial = None
			Driver.serial_ready = False
			Driver.received_line = None
			Driver.heartbeat_online = False
			Driver.heartbeat_recv = 0
			Driver.heartbeat_send = 0


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000_Driver.configure(self, configuration)
		self.config['heartbeat-period'] = configuration.getint('driver:webserial', 'heartbeat-period', fallback=1)
		self.config['trace'] = configuration.getboolean('driver:webserial', 'trace', fallback=False)
		self.config['tty']  = configuration.getstring(str(self), 'driver-tty', fallback='/dev/ttyHAL9000')
#todo: pin-sda,pin-scl from config
		while Driver.serial is None:
			try:
				self.logger.info(f"driver:webserial => Connecting to '{self.config['tty']}'...")
				Driver.serial = serial.Serial(port=self.config['tty'], timeout=0.01, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
				self.logger.debug('driver:webserial => ...opened, waiting for heartbeat...')
				while Driver.heartbeat_online is False:
					self.heartbeat()
					line = self.receive()
					time.sleep(0.1)
				self.logger.debug('driver:webserial => ...ready')
				self.send('["device/mcp23X17", {"init": {}}]')
			except:
				time.sleep(0.1)
				raise
		peripheral_type, peripheral_name = str(self).split(':', 1)
		if peripheral_type in ["rotary"]:
			input_pins = configuration.getlist(str(self), 'driver-pins', fallback="")
			if len(input_pins) != 2:
				self.logger.error('driver:webserial => invalid configuration for driver-pins, must be a list with two elements')
				return
			self.send('["device/mcp23X17", {"config": {"device": {"type": "%s", "name": "%s", "inputs": [{"pin": "%s", "label": "sigA"},{"pin": "%s", "label": "sigB"}]}}}]' % (peripheral_type, peripheral_name, input_pins[0], input_pins[1]))
		if peripheral_type in ["switch", "button", "toggle"]:
			input_pin = configuration.get(str(self), 'driver-pin', fallback="")
			if len(input_pin) != 2:
				self.logger.error('driver:webserial => invalid configuration for driver-pin, must be a single pin name (A0-A7,B0-B7)')
				return
			input_pin_pullup = configuration.getboolean(str(self), 'driver-pin-pullup', fallback=True)
			event_low  = configuration.getstring(str(self), 'event-low', fallback='on')
			event_high = configuration.getstring(str(self), 'event-high', fallback='off')
			self.send('["device/mcp23X17", {"config": {"device": {"type": "%s", "name": "%s", "inputs": [{"pin": "%s", "pullup": "%s", "label": "sigX"}], "events": {"low": "%s", "high": "%s"}}}}]' % (peripheral_type, peripheral_name, input_pin, str(input_pin_pullup).lower(), event_low, event_high))


	def receive(self):
		line = None
		data = Driver.serial.readline().decode('utf-8')
		if len(data) > 0:
			line = ""
			while len(data) and '\n' not in data:
				line += data.strip()
				data = Driver.serial.readline().decode('utf-8')
			line += data.strip()
		if line is not None:
			if len(line) == 0:
				Driver.heartbeat_recv = time.time()
				line = None
			else:
				if self.config['trace'] is True:
					self.logger.debug(f"USB(D->H): {line}")
		if (time.time()-Driver.heartbeat_recv) < (2*self.config['heartbeat-period']) and Driver.heartbeat_online == False:
			Driver.heartbeat_online = True
		if (time.time()-Driver.heartbeat_recv) >= (2*self.config['heartbeat-period']) and Driver.heartbeat_online == True:
			Driver.heartbeat_online = False
		return line


	def received(self):
		line = Driver.received_line
		Driver.received_line = ""
		return line


	def heartbeat(self):
		if time.time()-Driver.heartbeat_send > self.config['heartbeat-period']:
			self.send("")
			Driver.heartbeat_send = time.time()


	def send(self, line: str):
		if self.config['trace'] is True and len(line) > 0:
			self.logger.debug("USB(H->D): {}".format(line))
		if not line.endswith("\n"):
			line += "\n"
		Driver.serial.write(line.encode('utf-8'))
		Driver.serial.flush()


	def do_loop(self) -> bool:
		if Driver.serial_ready == False:
			self.send('["device/mcp23X17", {"start": true}]')
			Driver.serial_ready = True
		if time.time()-Driver.heartbeat_send >= 1:
			self.heartbeat()
		Driver.received_line = self.receive()
		return Driver.heartbeat_online

