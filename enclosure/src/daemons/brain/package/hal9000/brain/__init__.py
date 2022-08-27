#!/usr/bin/python3

from configparser import ConfigParser
from hal9000.daemon.plugin import HAL9000_Plugin


class HAL9000_Action(HAL9000_Plugin):
	def __init__(self, action_type: str, action_name: str, **kwargs) -> None:
		HAL9000_Plugin.__init__(self, 'action:{}:{}'.format(action_type, action_name))
		self.daemon = kwargs.get('daemon', None)
		self.config = dict()

	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name)

	def process(self, synapse_data: dict, cortex: dict) -> None:
		pass


class HAL9000_Trigger(HAL9000_Plugin):

	def __init__(self, trigger_type: str, trigger_name: str, **kwargs) -> None:
		HAL9000_Plugin.__init__(self, 'trigger:{}:{}'.format(trigger_type, trigger_name))
		self.daemon = kwargs.get('daemon', None)
		self.config = dict()

	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name)

	def handle(self) -> dict:
		return None

