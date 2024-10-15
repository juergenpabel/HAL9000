from re import match as re_match
from json import loads as json_loads
from jsonpath_ng.ext import parse as jsonpath_ng_ext_parse
from configparser import ConfigParser as configparser_ConfigParser
from aiomqtt import Message as aiomqtt_Message
from logging import getLogger as logging_getLogger

from hal9000.brain.daemon import Brain
from hal9000.brain.plugin import HAL9000_Trigger, HAL9000_Plugin_Data


class Trigger(HAL9000_Trigger):

	def __init__(self, trigger_name: str, plugin_status: HAL9000_Plugin_Data) -> None:
		HAL9000_Trigger.__init__(self, 'mqtt', trigger_name, plugin_status)
		self.payload_jsonpath_parser = None


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Trigger.configure(self, configuration, section_name)
		self.config['topic'] = configuration.getstring(section_name, 'mqtt-topic', fallback=None)
		self.config['payload-regex'] = configuration.getstring(section_name, 'mqtt-payload-regex', fallback=None)
		self.config['payload-jsonpath'] = configuration.getstring(section_name, 'mqtt-payload-jsonpath', fallback=None)
		self.config['signal-json-formatter'] = configuration.getstring(section_name, 'signal-json-formatter', fallback=None)
		if self.config['payload-jsonpath'] is not None:
			self.payload_jsonpath_parser = jsonpath_ng_ext_parse(self.config['payload-jsonpath'])


	def callbacks(self) -> dict:
		result = {}
		topics = []
		if self.config['topic'] is not None:
			topics.append(self.config['topic'])
		result['mqtt'] = topics
		return result


	def handle(self, message: aiomqtt_Message) -> dict:
		signal = None
		if self.config['signal-json-formatter'] is not None:
			try:
				logging_getLogger().log(Brain.LOGLEVEL_TRACE, f"[mqtt] Trigger.handle(): {message.topic} => {message.payload}")
				payload = message.payload.decode('utf-8', 'surrogateescape')
				if self.config['payload-regex'] is not None:
					matches = re_match(self.config['payload-regex'], payload)
					if matches is not None:
						signal = json_loads(self.config['signal-json-formatter'] % matches.groupdict())
				if self.config['payload-jsonpath'] is not None:
					for match in self.payload_jsonpath_parser.find(json_loads(f'[{payload}]')):
						signal = json_loads(self.config['signal-json-formatter'] % {'jsonpath': match.value})
			except Exception as e:
				logging_getLogger().error(f"Exception in MQTT.Trigger.handle(): {type(e)} => {str(e)}")
			if signal is not None:
				if isinstance(signal, list) is False:
					logging_getLogger().error(f"[trigger:mqtt] for message received on topic '{self.config['topic']}': '{signal}' is not " \
					                          f"an instance of python 'list', dropping it")
					signal = {}
				if len(signal) != 2 or isinstance(signal[0], str) is False or isinstance(signal[1], dict) is False:
					logging_getLogger().error(f"[trigger:mqtt] for message received on topic '{self.config['topic']}': '{signal}' is not " \
					                          f"a python 'list' with 2 elements of types 'str' and 'dict', dropping it")
		return signal

