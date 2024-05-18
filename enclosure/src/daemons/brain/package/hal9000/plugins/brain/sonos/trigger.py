#!/usr/bin/python3

from hal9000.brain.modules import HAL9000_Trigger
from configparser import ConfigParser

class Trigger(HAL9000_Trigger):

	def __init__(self, trigger_name: str) -> None:
		HAL9000_Trigger.__init__(self, 'sonos', trigger_name)


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		#print('TODO:trigger:sonos.config()')
		pass


	def handle(self) -> dict:
		print('TODO:trigger:sonos.handle()')
		return dict()

