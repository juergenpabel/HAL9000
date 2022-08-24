#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.brain import HAL9000_Action
from hal9000.brain.daemon import Daemon


class EnclosureComponent:
        def __init__(self, **kwargs) -> None:
                self.daemon = kwargs.get('daemon', None)


        def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
                pass


        def process(self, signal: dict, cortex: dict) -> None:
                pass


from .kalliope  import Kalliope
from .control import Control
from .volume  import Volume
from .motion  import Motion
from .rfid    import RFID


class Action(HAL9000_Action):
	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'enclosure', 'self', **kwargs)
		self.daemon = kwargs.get('daemon', None)
		self.components = dict()
		self.components['kalliope'] = Kalliope(**kwargs)
		self.components['control']  = Control(**kwargs)
		self.components['volume']   = Volume(**kwargs)
		self.components['motion']   = Motion(**kwargs)
		self.components['rfid']     = RFID(**kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		for component in self.components.keys():
			self.components[component].configure(configuration, section_name, cortex)


	def process(self, signal: dict, cortex: dict) -> None:
		for identifier in signal.keys():
			if identifier in self.components:
				self.components[identifier].process(signal, cortex)

