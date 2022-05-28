#!/usr/bin/python3

from hal9000.abstract.plugin import HAL9000_Action as HAL9000
from configparser import ConfigParser


class Action(HAL9000):
	def __init__(self) -> None:
		HAL9000.__init__(self, 'mqtt')
		print('action:mqtt.init()')


	def configure(self, configuration: ConfigParser, section: str) -> None:
		print('action:mqtt.config()')


	def process(self, data: dict) -> None:
		print('action:mqtt.process()')

