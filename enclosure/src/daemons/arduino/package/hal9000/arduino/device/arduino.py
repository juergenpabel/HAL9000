#!/usr/bin/python3

import sys
import json
import logging
from configparser import ConfigParser

from hal9000.arduino.device import HAL9000_Device
from hal9000.arduino.driver import HAL9000_Driver


class Device(HAL9000_Device):

	def __init__(self, name: str, Driver: HAL9000_Driver) -> None:
		HAL9000_Device.__init__(self, 'arduino:{}'.format(name), Driver)
		self.config = dict()
		self.driver = None
		self.logger = logging.getLogger()
		self.current_uid = None
 

	def configure(self, configuration: ConfigParser, section_name: str = None) -> None:
		HAL9000_Device.configure(self, configuration)
		device_type, device_name = str(self).split(':')
		self.config['enabled'] = configuration.getboolean(str(self), 'enabled', fallback=True)
		if self.config['enabled']:
			self.config['name'] = configuration.get(str(self), 'name', fallback=None)
			self.driver = self.Driver('{}:{}'.format(configuration.getstring(str(self), 'driver'), device_name))
			self.driver.configure(configuration)


	def do_loop(self, callback_event = None) -> bool:
		if self.driver is not None:
			if self.driver.do_loop():
				line = self.driver.status['read']
				if len(line) > 0 and line.startswith('[') and line.endswith(']'):
					event, payload = json.loads(line)
					if event != "syslog" and 'device' in payload:
						if callback_event is not None:
							device_type=payload["device"]["type"]
							device_name=payload["device"]["name"]
							if self.config['name'] is not None:
								device_name = self.config['name']
							if device_type == "rotary":
								callback_event(device_type, device_name, "delta", payload["event"]["delta"])
							if device_type in ["switch", "button", "toggle"]:
								callback_event(device_type, device_name, "status", payload["event"]["status"])
				return True
		return False

