from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import Brain
from hal9000.brain.plugins.enclosure import EnclosureComponent


class Motion(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, 'trigger:enclosure:motion', **kwargs)


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		EnclosureComponent.configure(self, configuration, section_name)
#TODO		self.daemon.plugins['enclosure'].addLocalNames('motion_timestamp')
#TODO		self.daemon.plugins['enclosure'].motion_timestamp = None

