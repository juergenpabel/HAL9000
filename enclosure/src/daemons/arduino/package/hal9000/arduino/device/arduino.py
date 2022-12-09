#!/usr/bin/python3

import sys
import time
import json
import logging
from configparser import ConfigParser
from datetime import datetime, timezone

from hal9000.arduino.device import HAL9000_Device
from hal9000.arduino.driver import HAL9000_Driver


class Device(HAL9000_Device):

	def __init__(self, name: str, driver: HAL9000_Driver) -> None:
		HAL9000_Device.__init__(self, name, driver)
 

	def do_loop(self, callback_event = None) -> bool:
		if self.driver.do_loop():
			line = self.driver.received()
			if line is not None and len(line) > 0 and line.startswith('[') and line.endswith(']'):
				try:
					topic, payload = json.loads(line)
					if topic.startswith("syslog/"):
						log_level = logging.WARN
						syslog, level = topic.split('/', 1)
						if isinstance(level, str):
							if hasattr(logging, level.upper()):
								log_level = getattr(logging, level.upper())
						self.logger.log(log_level, payload)
					if topic == "system/time" and 'sync' in payload:
						if payload['sync']['format'] == "epoch":
							data = {"sync": {"epoch": int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds)}}
							self.driver.send(json.dumps([topic, data]))
					if topic == "device/event" and 'device' in payload:
						device_type=payload["device"]["type"]
						device_name=payload["device"]["name"]
						if callback_event is not None:
							if device_type in ["rotary"]:
								callback_event(device_type, device_name, "delta", payload["event"]["delta"])
							if device_type in ["switch", "button", "toggle"]:
								callback_event(device_type, device_name, "status", payload["event"]["status"])
				except json.decoder.JSONDecodeError as e:
					self.logger.warn(e)
			return True
		return False


