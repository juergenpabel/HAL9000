#!/usr/bin/python3

import sys
import json
import logging
from configparser import ConfigParser

from hal9000.arduino.device import HAL9000_Device
from hal9000.arduino.driver import HAL9000_Driver


class Device(HAL9000_Device):

	def __init__(self, name: str, driver: HAL9000_Driver) -> None:
		HAL9000_Device.__init__(self, name, driver)
 

	def do_loop(self, callback_event = None) -> bool:
		if self.driver.do_loop():
			line = self.driver.received()
			if len(line) > 0 and line.startswith('[') and line.endswith(']'):
				event, payload = json.loads(line)
				if event != "syslog" and 'device' in payload:
					if callback_event is not None:
						device_type=payload["device"]["type"]
						device_name=payload["device"]["name"]
						if device_type in ["rotary"]:
							callback_event(device_type, device_name, "delta", payload["event"]["delta"])
						if device_type in ["switch", "button", "toggle"]:
							callback_event(device_type, device_name, "status", payload["event"]["status"])
			return True
		return False

