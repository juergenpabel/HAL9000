#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.plugins.brain.enclosure import EnclosureComponent


class Motion(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		EnclosureComponent.configure(self, configuration, section_name, cortex)


	def process(self, signal: dict, cortex: dict) -> None:
		EnclosureComponent.process(self, signal, cortex)

