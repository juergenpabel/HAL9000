#!/usr/bin/env python3

import logging
import time
import serial
import json
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
			Driver.send_queue = []


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000_Driver.configure(self, configuration)
		self.config['trace'] = configuration.getboolean('driver:webserial', 'trace', fallback=False)
		self.config['tty']  = configuration.getstring(str(self), 'driver-tty', fallback='/dev/ttyHAL9000')
#todo: pin-sda,pin-scl from config
		if Driver.serial is None:
			self.logger.info(f"driver:webserial => Connecting to '{self.config['tty']}'...")
		while Driver.serial is None:
			try:
				Driver.serial = serial.Serial(port=self.config['tty'], timeout=0.01, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
				self.logger.debug('driver:webserial => ...ready')
				data = {}
				self.send('["application/runtime", {"status": "?"}]', True)
				while "status" not in data or data["status"] == "booting":
					line = self.receive()
					if line is not None and line.startswith('["application/runtime"'):
						data = json.loads(line)
						if len(data) == 2:
							data = data[1]
						else:
							data = {}
				if data["status"] == "configuring":
					i2c_bus  = configuration.getint('mcp23X17', 'i2c-bus', fallback=0)
					i2c_addr = configuration.getint('mcp23X17', 'i2c-address', fallback=32)
					self.send('["device/mcp23X17", {"init": {"i2c-bus": %d, "i2c-address": %d}}]' % (i2c_bus, i2c_addr), True)
				if data["status"] == "running":
					Driver.serial_ready = True
					self.send('["application/runtime", {"status": "?"}]', True)
			except:
				time.sleep(0.1)
		if Driver.serial_ready is True:
			return
		peripheral_type, peripheral_name = str(self).split(':', 1)
		if peripheral_type in ["rotary"]:
			input_pins = configuration.getlist(str(self), 'mcp23X17-pins', fallback="")
			if len(input_pins) != 2:
				self.logger.error('driver:webserial => invalid configuration for mcp23X17-pins, must be a list with two elements')
				return
			self.send('["device/mcp23X17", {"config": {"device": {"type": "%s", "name": "%s", "inputs": [{"pin": "%s", "label": "sigA"},{"pin": "%s", "label": "sigB"}]}}}]' % (peripheral_type, peripheral_name, input_pins[0], input_pins[1]), True)
		if peripheral_type in ["switch", "button", "toggle"]:
			input_pin = configuration.get(str(self), 'mcp23X17-pin', fallback="")
			if len(input_pin) != 2:
				self.logger.error('driver:webserial => invalid configuration for mcp23X17-pin, must be a single pin name (A0-A7,B0-B7)')
				return
			input_pin_pullup = configuration.getboolean(str(self), 'mcp23X17-pin-pullup', fallback=True)
			event_low  = configuration.getstring(str(self), 'event-low', fallback='on')
			event_high = configuration.getstring(str(self), 'event-high', fallback='off')
			self.send('["device/mcp23X17", {"config": {"device": {"type": "%s", "name": "%s", "inputs": [{"pin": "%s", "pullup": "%s", "label": "sigX"}], "events": {"low": "%s", "high": "%s"}}}}]' % (peripheral_type, peripheral_name, input_pin, str(input_pin_pullup).lower(), event_low, event_high), True)


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
			if self.config['trace'] is True:
				self.logger.debug(f"USB(D->H): {line}")
		return line


	def received(self):
		line = Driver.received_line
		Driver.received_line = ""
		return line


	def send(self, line: str, force = False):
		if Driver.serial_ready is False and force is False:
			Driver.send_queue.append(line)
			return
		if self.config['trace'] is True and len(line) > 0:
			self.logger.debug("USB(H->D): {}".format(line))
		if not line.endswith("\n"):
			line += "\n"
		Driver.serial.write(line.encode('utf-8'))
		Driver.serial.flush()


	def do_loop(self) -> bool:
		if Driver.serial_ready is False:
			self.send('["device/mcp23X17", {"start": true}]', True)
			self.send('["", ""]', True)
			Driver.serial_ready = True
			for line in Driver.send_queue:
				self.send(line)
			Driver.send_queue.clear()
			self.send('["application/runtime", {"status": "?"}]', True)
		Driver.received_line = self.receive()
		return True

