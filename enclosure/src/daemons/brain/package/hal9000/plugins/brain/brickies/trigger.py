#!/usr/bin/python3

from hal9000.abstract.plugin import HAL9000_Trigger as HAL9000
from configparser import ConfigParser

class Trigger(HAL9000):
	def __init__(self, trigger_name: str) -> None:
		HAL9000.__init__(self, 'brickies', trigger_name)


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		print('TODO:trigger:brickies.config()')


	def handle(self) -> dict:
		print('TODO:trigger:brickies.handle()')
		return dict()

