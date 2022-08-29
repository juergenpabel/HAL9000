#!/usr/bin/env python3

import logging
import time
import json
from datetime import datetime, timezone
import serial
from configparser import ConfigParser

from . import HAL9000_Driver as HAL9000


class Driver(HAL9000):

	def __init__(self, name: str):
		HAL9000.__init__(self, name)
		self.config = dict()
		if hasattr(Driver, 'serial') is False:
			Driver.serial = None
			Driver.status = dict()
			Driver.status['read'] = None
		self.logger = logging.getLogger()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.config['tty'] = configuration.getstring(str(self), 'tty', fallback="/dev/ttyRP2040")
		self.config['hardware'] = configuration.getstring(str(self), 'hardware')
		self.config['software'] = configuration.getstring(str(self), 'software')
		self.config['pins'] = configuration.getlist(str(self), 'pins')
		while Driver.serial is None:
			try:
				self.logger.debug('driver:{} => Connecting to {}'.format(str(self), self.config['tty']))
				Driver.serial = serial.Serial(port=self.config['tty'], timeout=0.1, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
				self.logger.debug('driver:{} => connected...'.format(str(self)))
				line = self.receive()
				while "loop()" not in line:
					line = self.receive()
				self.logger.debug('driver:{} => ...waiting...'.format(str(self)))
				self.send('["device/mcp23X17", {"init": {}}]')
			except:
				time.sleep(0.1)
		if self.config['software'] == "rotary":
			self.send('["device/mcp23X17", {"config": {"device": {"name": "%s",    "type": "%s", "inputs": [{"pin": "%s", "label": "sigA"},{"pin": "%s", "label": "sigB"}]}}}]' % (str(self).split(':')[1], self.config['software'], self.config['pins'][0], self.config['pins'][1]))
		if self.config['software'] in ["switch", "button", "toggle"]:
			self.send('["device/mcp23X17", {"config": {"device": {"name": "%s",    "type": "%s", "inputs": [{"pin": "%s", "label": "sigX"}], "actions": {"true": "on", "false": "off"}}}}]' % (str(self).split(':')[1], self.config['software'], self.config['pins'][0]))
		time.sleep(0.1)
		self.send('["system/time", {"config": {"interval": 60}}]')
		self.logger.debug('driver:{} => ...and configured'.format(str(self)))



	def receive(self):
		line = ""
		data = Driver.serial.readline().decode('utf-8')
		while len(data) and '\n' not in data:
			line += data
			data = Driver.serial.readline().decode('utf-8')
		line += data.strip()
		if len(line):
			print("USB(D->H): {}".format(line))
		return line


	def send(self, line: str):
		print("USB(H->D): {}".format(line))
		if not line.endswith("\n"):
			line += "\n"
		Driver.serial.write(line.encode('utf-8'))


	def do_loop(self) -> bool:
		if Driver.status['read'] is None:
			self.send('["device/mcp23X17", {"start": true}]')
		Driver.status['read'] = self.receive()
		if len(Driver.status['read']) > 0 and Driver.status['read'].startswith('[') and Driver.status['read'].endswith(']'):
			event, payload = json.loads(Driver.status['read'])
			if event == "system/time":
				if payload['sync']['format'] == "epoch":
					self.send('["system/time",{"sync":{"epoch":'+str(int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))+'}}]')
					Driver.status['read'] = ""
		return True

