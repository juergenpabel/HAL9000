#!/usr/bin/python3

from hal9000.abstract.plugin import HAL9000_Action as HAL9000
from configparser import ConfigParser


class Action(HAL9000):
	def __init__(self, action_name: str) -> None:
		HAL9000.__init__(self, 'brickies', action_name)


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		print('TODO:action:brickies.config()')


	def process(self, synapse_data: dict, brain_data: dict) -> None:
		print('TODO:action:brickies.process()')

