#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.brain.plugins.enclosure import EnclosureComponent


class Motion(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		EnclosureComponent.configure(self, configuration, section_name)
#TODO		self.daemon.cortex['plugin']['enclosure'].addNames('motion_timestamp')
#TODO		self.daemon.cortex['plugin']['enclosure'].motion_timestamp = None

