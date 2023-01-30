#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.daemon.arduino import Daemon
from hal9000.daemon.arduino.plugins.enclosure import EnclosureComponent


class RFID(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		EnclosureComponent.configure(self, configuration, section_name, cortex)
		if 'rfid' not in cortex['enclosure']:
			cortex['enclosure']['rfid'] = dict()
			cortex['enclosure']['rfid']['uid'] = None


	def process(self, signal: dict, cortex: dict) -> None:
		EnclosureComponent.process(self, signal, cortex)

