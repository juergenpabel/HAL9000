#!/usr/bin/python3

import re
import json
from configparser import ConfigParser

from hal9000.daemon.enclosure.modules import HAL9000_Trigger


class Trigger(HAL9000_Trigger):

	def __init__(self, trigger_name: str) -> None:
		HAL9000_Trigger.__init__(self, 'mqtt', trigger_name)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		self.config['topic'] = configuration.getstring(section_name, 'mqtt-topic', fallback=None)
		self.config['payload-regex'] = configuration.getstring(section_name, 'mqtt-payload-regex', fallback=None)
		self.config['neuron-json-formatter'] = configuration.getstring(section_name, 'neuron-json-formatter', fallback=None)


	def callbacks(self) -> dict:
		result = dict()
		topics = list()
		if self.config['topic'] is not None:
			topics.append(self.config['topic'])
		result['mqtt'] = topics
		return result


	def handle(self, message) -> dict:
		neuron = None
		matches = re.match(self.config['payload-regex'], message.payload.decode('utf-8'))
		if matches is not None:
			neuron = matches.groupdict()
			formatter = self.config['neuron-json-formatter']
			if formatter is not None:
				neuron = json.loads(formatter % neuron)
		return neuron

