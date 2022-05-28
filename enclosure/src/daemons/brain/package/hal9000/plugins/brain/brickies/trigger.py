#!/usr/bin/python3

from hal9000.abstract.plugin import HAL9000_Trigger as HAL9000
from configparser import ConfigParser

class Trigger(HAL9000):
	def __init__(self) -> None:
		HAL9000.__init__(self, 'brickies')
		print('trigger:brickies.init()')


	def configure(self, configuration: ConfigParser, section: str) -> None:
		print('trigger:brickies.config()')


	def handle(self) -> dict:
		print('trigger:brickies.handle()')
		return dict()

