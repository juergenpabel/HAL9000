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



class Action(HAL9000_Action):
	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'enclosure', 'self', **kwargs)
		self.daemon = kwargs.get('daemon', None)
		self.components = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		for identifier in configuration.options('enclosure:components'):
			module_id = configuration.get('enclosure:components', identifier, fallback=None)
			if module_id is not None:
				module_path, module_class = module_id.rsplit('.', 1)
				Component = self.daemon.import_plugin(module_path, module_class)
				if Component is not None:
					self.components[identifier] = Component(daemon=self.daemon)
		for identifier in self.components.keys():
			self.components[identifier].configure(configuration, section_name, cortex)


	def process(self, signal: dict, cortex: dict) -> None:
		for identifier in signal.keys():
			if identifier in self.components:
				self.components[identifier].process(signal, cortex)

