#!/usr/bin/python3

from configparser import ConfigParser
from hal9000.daemon.plugin import HAL9000_Plugin


class HAL9000_Action(HAL9000_Plugin):
	def __init__(self, action_type: str, action_name: str) -> None:
		HAL9000_Plugin.__init__(self, 'action:{}:{}'.format(action_type, action_name))

	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict = None) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name)

	def process(self, synapse_data: dict, brain_data: dict) -> None:
		pass


class HAL9000_Trigger(HAL9000_Plugin):

	def __init__(self, trigger_type: str, trigger_name: str) -> None:
		HAL9000_Plugin.__init__(self, 'trigger:{}:{}'.format(trigger_type, trigger_name))

	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict = None) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name)

	def handle(self) -> dict:
		return None

