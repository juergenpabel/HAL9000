#!/usr/bin/env python3

import logging
import time
import json
import serial
from configparser import ConfigParser
from datetime import datetime, timezone

from . import HAL9000_Driver


class Driver(HAL9000_Driver):

	def __init__(self, name: str):
		HAL9000_Driver.__init__(self, name)
		self.config = dict()
		if hasattr(Driver, 'serial') is False:
			Driver.serial = None
			Driver.received_line = None


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000_Driver.configure(self, configuration)
		self.config['webserial:trace'] = configuration.getboolean('driver:webserial', 'trace', fallback=False)
		self.config['tty']  = configuration.getstring(str(self), 'driver-tty', fallback='/dev/ttyHAL9000')
#todo: pin-sda,pin-scl from config
		while Driver.serial is None:
			try:
				self.logger.info('driver:webserial => Connecting to {}'.format(self.config['tty']))
				Driver.serial = serial.Serial(port=self.config['tty'], timeout=0.01, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
				self.logger.debug('driver:webserial => ...connected')
				self.send('run')
				self.logger.debug('driver:webserial => waiting for loop()...')
				line = self.receive()
				while "loop()" not in line:
					line = self.receive()
				Driver.received_line = None
				self.logger.debug('driver:webserial => ...loop() reached')
				self.send('["device/mcp23X17", {"init": {}}]')
			except:
				time.sleep(0.1)
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
		line = ""
		data = Driver.serial.readline().decode('utf-8')
		while len(data) and '\n' not in data:
			line += data
			data = Driver.serial.readline().decode('utf-8')
		line += data.strip()
		if len(line):
			if self.config['webserial:trace'] is True:
				self.logger.debug("USB(D->H): {}".format(line))
		return line


	def received(self):
		result = Driver.received_line
		Driver.received_line = ""
		return result


	def send(self, line: str):
		if self.config['webserial:trace'] is True:
			self.logger.debug("USB(H->D): {}".format(line))
		if not line.endswith("\n"):
			line += "\n"
		Driver.serial.write(line.encode('utf-8'))


	def do_loop(self) -> bool:
		if Driver.received_line is None:
			self.send('["device/mcp23X17", {"start": true}]')
			time.sleep(0.1)
			self.logger.debug('driver:webserial => ...and started')
		Driver.received_line = self.receive()
		if len(Driver.received_line) > 0 and Driver.received_line.startswith('[') and Driver.received_line.endswith(']'):
			if Driver.received_line.startswith('["syslog"'):
				Driver.received_line = ""
				return True
			try:
				event, payload = json.loads(Driver.received_line)
				if event == "system/time":
					if payload['sync']['format'] == "epoch":
						self.send('["system/time",{"sync":{"epoch":'+str(int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))+'}}]')
						Driver.received_line = ""
			except json.decoder.JSONDecodeError:
				Driver.received_line = ""
		return True

