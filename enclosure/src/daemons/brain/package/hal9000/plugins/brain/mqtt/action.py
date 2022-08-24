#!/usr/bin/python3

from hal9000.brain import HAL9000_Action
from configparser import ConfigParser


class Action(HAL9000_Action):
	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'mqtt', action_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		print('TODO:action:mqtt.config()')


	def process(self, synapse_data: dict, cortex: dict) -> dict:
		print('TODO:action:mqtt.process()')
		return dict()

