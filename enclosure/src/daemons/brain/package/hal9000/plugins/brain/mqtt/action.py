#!/usr/bin/python3

from configparser import ConfigParser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain import HAL9000_Action


class Action(HAL9000_Action):
	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'mqtt', action_name, **kwargs)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		self.config['topic'] = configuration.get(section_name, 'mqtt-topic', fallback=None)
		self.config['payload'] = configuration.get(section_name, 'mqtt-payload', fallback=None)


	def process(self, synapse_data: dict, cortex: dict) -> None:
		mqtt_publish_message(self.config['topic'], self.config['payload'])

