#!/usr/bin/python3

import json
from configparser import ConfigParser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.agent.modules import HAL9000_Action


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
				mqtt_publish_message(mqtt_topic, str(mqtt_payload))

