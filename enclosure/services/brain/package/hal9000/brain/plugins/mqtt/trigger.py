from re import match as re_match
from json import loads as json_loads
from jsonpath_ng.ext import parse as jsonpath_ng_ext_parse
from configparser import ConfigParser as configparser_ConfigParser

import logging

from hal9000.brain.plugin import HAL9000_Trigger, HAL9000_Plugin_Status


class Trigger(HAL9000_Trigger):

	def __init__(self, trigger_name: str, trigger_status: HAL9000_Plugin_Status) -> None:
		HAL9000_Trigger.__init__(self, 'mqtt', trigger_name, trigger_status)
		self.config = dict()
		self.payload_jsonpath_parser = None


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		self.config['topic'] = configuration.getstring(section_name, 'mqtt-topic', fallback=None)
		self.config['payload-regex'] = configuration.getstring(section_name, 'mqtt-payload-regex', fallback=None)
		self.config['payload-jsonpath'] = configuration.getstring(section_name, 'mqtt-payload-jsonpath', fallback=None)
		self.config['signal-json-formatter'] = configuration.getstring(section_name, 'signal-json-formatter', fallback=None)
		if self.config['payload-jsonpath'] is not None:
			self.payload_jsonpath_parser = jsonpath_ng_ext_parse(self.config['payload-jsonpath'])


	def callbacks(self) -> dict:
		result = dict()
		topics = list()
		if self.config['topic'] is not None:
			topics.append(self.config['topic'])
		result['mqtt'] = topics
		return result


	def handle(self, message) -> dict:
		signal = {}
		if self.config['signal-json-formatter'] is not None:
			try:
				payload = message.payload.decode('utf-8')
				if self.config['payload-regex'] is not None:
					matches = re_match(self.config['payload-regex'], payload)
					if matches is not None:
						signal = json_loads(self.config['signal-json-formatter'] % matches.groupdict())
				if self.config['payload-jsonpath'] is not None:
					for match in self.payload_jsonpath_parser.find(json_loads(f'[{payload}]')):
						signal = json_loads(self.config['signal-json-formatter'] % {'jsonpath': match.value})
			except Exception as e:
				self.daemon.logger.error(f"Exception in MQTT.Trigger.handle() => {e}")
		return signal

