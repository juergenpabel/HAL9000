#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.agent.daemon import Daemon
from hal9000.plugins.agent.enclosure import EnclosureComponent


class Motion(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		EnclosureComponent.configure(self, configuration, section_name, cortex)
		if 'motion' not in cortex['enclosure']:
			cortex['enclosure']['motion'] = dict()
			cortex['enclosure']['motion']['timestamp'] = None


	def process(self, signal: dict, cortex: dict) -> None:
		EnclosureComponent.process(self, signal, cortex)

