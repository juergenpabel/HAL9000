from re import match as re_match
from json import loads as json_loads
from jsonpath_ng.ext import parse as jsonpath_ng_ext_parse
from configparser import ConfigParser as configparser_ConfigParser
from aiomqtt import Message as aiomqtt_Message

from hal9000.brain.daemon import Daemon
from hal9000.brain.plugin import HAL9000_Trigger, RUNLEVEL, CommitPhase


class Trigger(HAL9000_Trigger):

	def __init__(self, trigger_name: str, **kwargs) -> None:
		super().__init__(trigger_name, **kwargs)
		self.module.payload_jsonpath_parser = None
		self.runlevel = RUNLEVEL.RUNNING, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.config['topic'] = configuration.getstring(section_name, 'mqtt-topic', fallback=None)
		self.module.config['payload-regex'] = configuration.getstring(section_name, 'mqtt-payload-regex', fallback=None)
		self.module.config['payload-jsonpath'] = configuration.getstring(section_name, 'mqtt-payload-jsonpath', fallback=None)
		self.module.config['signal-json-formatter'] = configuration.getstring(section_name, 'signal-json-formatter', fallback=None)
		if self.module.config['payload-jsonpath'] is not None:
			self.module.payload_jsonpath_parser = jsonpath_ng_ext_parse(self.module.config['payload-jsonpath'])


	def callbacks(self) -> dict:
		result = {}
		topics = []
		if self.module.config['topic'] is not None:
			topics.append(self.module.config['topic'])
		result['mqtt'] = topics
		return result


	def handle(self, message: aiomqtt_Message) -> dict:
		signal = None
		if self.module.config['signal-json-formatter'] is not None:
			try:
				self.module.daemon.logger.log(Daemon.LOGLEVEL_TRACE, f"[mqtt] Trigger.handle(): {message.topic} => {message.payload}")
				payload = message.payload.decode('utf-8', 'surrogateescape')
				if self.module.config['payload-regex'] is not None:
					matches = re_match(self.module.config['payload-regex'], payload)
					if matches is not None:
						signal = json_loads(self.module.config['signal-json-formatter'] % matches.groupdict())
				if self.module.config['payload-jsonpath'] is not None:
					for match in self.module.payload_jsonpath_parser.find(json_loads(f'[{payload}]')):
						signal = json_loads(self.module.config['signal-json-formatter'] % {'jsonpath': match.value})
			except Exception as e:
				self.module.daemon.logger.error(f"Exception in MQTT.Trigger.handle(): {type(e)} => {str(e)}")
			if signal is not None:
				if isinstance(signal, list) is False:
					self.module.daemon.logger.error(f"[trigger:mqtt] for message received on topic '{self.module.config['topic']}': " \
					                                f"'{signal}' is not an instance of python 'list', dropping it")
					signal = {}
				if len(signal) != 2 or isinstance(signal[0], str) is False or isinstance(signal[1], dict) is False:
					self.module.daemon.logger.error(f"[trigger:mqtt] for message received on topic '{self.module.config['topic']}': " \
					                                f"'{signal}' is not a python 'list' with 2 elements of types 'str' and 'dict', dropping it")
		return signal

