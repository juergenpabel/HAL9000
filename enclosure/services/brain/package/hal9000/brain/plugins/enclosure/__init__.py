#!/usr/bin/python3

import json
from configparser import ConfigParser

from hal9000.brain.plugin import HAL9000_Action
from hal9000.brain.daemon import Daemon


class EnclosureComponent:
	def __init__(self, **kwargs) -> None:
		self.daemon = kwargs.get('daemon', None)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		pass



class Action(HAL9000_Action):
	def __init__(self, action_name: str, plugin_cortex, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'enclosure', 'self', plugin_cortex, **kwargs)
		self.components = dict()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		for identifier in configuration.options('enclosure:components'):
			plugin_id = configuration.get('enclosure:components', identifier, fallback=None)
			if plugin_id is not None:
				plugin_path, plugin_class = plugin_id.rsplit('.', 1)
				Component = self.daemon.import_plugin(plugin_path, plugin_class)
				if Component is not None:
					self.components[identifier] = Component(daemon=self.daemon)
		for identifier in self.components.keys():
			self.components[identifier].configure(configuration, section_name)


	def runlevel(self) -> str:
		return HAL9000_Action.PLUGIN_RUNLEVEL_RUNNING

