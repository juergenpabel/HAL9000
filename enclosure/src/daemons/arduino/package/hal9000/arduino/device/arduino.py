#!/usr/bin/python3

import sys
import time
import json
import logging
from configparser import ConfigParser
from datetime import datetime, timezone
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.arduino.device import HAL9000_Device
from hal9000.arduino.driver import HAL9000_Driver


class Device(HAL9000_Device):

	def __init__(self, name: str, driver: HAL9000_Driver) -> None:
		HAL9000_Device.__init__(self, name, driver)
		if hasattr(Device, 'status') is False:
			Device.status = "offline"
 

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
					if topic == "application/runtime" and 'status' in payload:
						if payload["status"] == "running":
							self.mqtt_publish_status('online')
						if payload["status"] in ["resetting", "halting"]:
							self.mqtt_publish_status('offline')
					if topic == "application/event" and 'error' in payload:
						self.mqtt_publish_error(payload)
					if topic == "gui/event" and 'screen' in payload:
						self.mqtt_publish_screen(payload)
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


	def mqtt_publish_status(self, status):
		if Device.status != status:
			Device.status = status
			mqtt_topic = 'hal9000/event/arduino/webserial/state'
			mqtt_payload = status
			mqtt_publish_message(mqtt_topic, mqtt_payload)
			self.logger.debug('MQTT published: {} => {}'.format(mqtt_topic, mqtt_payload))


	def mqtt_publish_screen(self, screen):
		mqtt_topic = 'hal9000/event/arduino/gui/screen'
		mqtt_payload = json.dumps(screen)
		mqtt_publish_message(mqtt_topic, mqtt_payload)
		self.logger.debug('MQTT published: {} => {}'.format(mqtt_topic, mqtt_payload))


	def mqtt_publish_error(self, error):
		mqtt_topic = 'hal9000/event/arduino/application/error'
		mqtt_payload = json.dumps(error)
		mqtt_publish_message(mqtt_topic, mqtt_payload)
		self.logger.debug('MQTT published: {} => {}'.format(mqtt_topic, mqtt_payload))

