#!/usr/bin/python3

import re
from configparser import ConfigParser

from hal9000.brain import HAL9000_Trigger


class Trigger(HAL9000_Trigger):

	def __init__(self, trigger_name: str) -> None:
		HAL9000_Trigger.__init__(self, 'mqtt', trigger_name)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		self.config['topic'] = configuration.getstring(section_name, 'mqtt-topic', fallback=None)
		self.config['payload-regex'] = configuration.getstring(section_name, 'mqtt-payload-regex', fallback=None)


	def callbacks(self) -> dict:
		result = dict()
		topics = list()
		if self.config['topic'] is not None:
			topics.append(self.config['topic'])
		result['mqtt'] = topics
		return result


	def handle(self, message) -> dict:
		matches = re.match(self.config['payload-regex'], message.payload.decode('utf-8'))
		if matches is not None:
			return matches.groupdict()
		return None

