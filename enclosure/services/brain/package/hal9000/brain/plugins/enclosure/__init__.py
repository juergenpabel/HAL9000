from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin_Data


class EnclosureComponent:
	def __init__(self, **kwargs) -> None:
		self.daemon = kwargs.get('daemon', None)
		self.config = {}


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		pass



class Action(HAL9000_Action):
	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'enclosure', 'self', plugin_status, **kwargs)
		self.components = {}


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
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
		return HAL9000_Action.RUNLEVEL_RUNNING

