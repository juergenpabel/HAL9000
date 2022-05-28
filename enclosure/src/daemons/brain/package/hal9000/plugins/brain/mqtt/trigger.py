#!/usr/bin/python3

from hal9000.abstract.plugin import HAL9000_Trigger as HAL9000
from configparser import ConfigParser


class Trigger(HAL9000):

	def __init__(self) -> None:
		HAL9000.__init__(self, 'mqtt')
		self.config = dict()


	def configure(self, configuration: ConfigParser, section: str) -> None:
		self.config['topic'] = configuration.getstring(section, 'mqtt-topic', fallback=None)
		self.config['payload-regex'] = configuration.getstring(section, 'mqtt-payload-regex', fallback=None)
		print(self.config['topic'])


	def callbacks(self) -> dict:
		result = list()
		if self.config['topic'] is not None:
			result.append(self.config['topic'])
		return result


	def handle(self, message) -> dict:
		print('trigger:mqtt.handle() => {}'.format(message.topic))
		data = dict()
		return data

