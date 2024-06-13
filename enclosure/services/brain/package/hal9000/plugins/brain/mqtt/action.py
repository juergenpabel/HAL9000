#!/usr/bin/python3

import os
import json
from configparser import ConfigParser

from hal9000.brain.modules import HAL9000_Module, HAL9000_Action


class Action(HAL9000_Action):
	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'mqtt', action_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		pass


	def process(self, signal: dict, cortex: dict) -> None:
		if 'mqtt' in signal:
			messages = signal['mqtt']
			if(isinstance(messages, list) == False):
				messages = [messages]
			for message in messages:
				mqtt_topic = message['topic']
				mqtt_payload = message['payload']
				if isinstance(mqtt_payload, str) is False:
					mqtt_payload = json.dumps(mqtt_payload)
				self.daemon.mqtt.publish(mqtt_topic, mqtt_payload)

	def runlevel(self, cortex: dict) -> str:
		return HAL9000_Module.MODULE_RUNLEVEL_RUNNING

