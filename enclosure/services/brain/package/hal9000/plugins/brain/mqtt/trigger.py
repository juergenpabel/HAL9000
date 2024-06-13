#!/usr/bin/python3

from re import match as re_match
from json import loads as json_loads
from jsonpath_ng.ext import parse as jsonpath_ng_ext_parse
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.modules import HAL9000_Trigger


class Trigger(HAL9000_Trigger):

	def __init__(self, trigger_name: str) -> None:
		HAL9000_Trigger.__init__(self, 'mqtt', trigger_name)
		self.config = dict()


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		self.config['topic'] = configuration.getstring(section_name, 'mqtt-topic', fallback=None)
		self.config['payload-regex'] = configuration.getstring(section_name, 'mqtt-payload-regex', fallback=None)
		self.config['payload-jsonpath'] = configuration.getstring(section_name, 'mqtt-payload-jsonpath', fallback=None)
		self.config['neuron-json-formatter'] = configuration.getstring(section_name, 'neuron-json-formatter', fallback=None)


	def callbacks(self) -> dict:
		result = dict()
		topics = list()
		if self.config['topic'] is not None:
			topics.append(self.config['topic'])
		result['mqtt'] = topics
		return result


	def handle(self, message) -> dict:
		neuron = {}
		if self.config['neuron-json-formatter'] is not None:
			try:
				payload = message.payload.decode('utf-8')
				if self.config['payload-regex'] is not None:
					matches = re_match(self.config['payload-regex'], payload)
					if matches is not None:
						neuron = json_loads(self.config['neuron-json-formatter'] % matches.groupdict())
				if self.config['payload-jsonpath'] is not None:
					for match in jsonpath_ng_ext_parse(self.config['payload-jsonpath']).find(json_loads(f'[{payload}]')):
						neuron = json_loads(self.config['neuron-json-formatter'] % {'jsonpath': match.value})
			except Exception as e:
				print(e)
		return neuron

