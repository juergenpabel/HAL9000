#!/usr/bin/python3

import json
from configparser import ConfigParser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain import HAL9000_Action


class Action(HAL9000_Action):
	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'mqtt', action_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		pass


	def process(self, synapse_data: dict, cortex: dict) -> None:
		mqtt_topic = synapse_data['mqtt']['topic']
		mqtt_payload = synapse_data['mqtt']['payload']['data']
		if synapse_data['mqtt']['payload']['type'] == "json":
			mqtt_payload = json.loads(mqtt_payload)
		mqtt_publish_message(mqtt_topic, str(mqtt_payload))

