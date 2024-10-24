from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, RUNLEVEL, CommitPhase


class EnclosureComponent:
	def __init__(self, id: str, **kwargs) -> None:
		self.id = id
		self.daemon = kwargs.get('daemon')


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		self.config = {}



class Action(HAL9000_Action):
	def __init__(self, action_name: str, **kwargs) -> None:
		super().__init__('enclosure', **kwargs)
		self.module.hidden = True
		self.module.components = {}
		self.runlevel = RUNLEVEL.RUNNING, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		for identifier in configuration.options('enclosure:components'):
			plugin_id = configuration.get('enclosure:components', identifier, fallback=None)
			if plugin_id is not None:
				plugin_path, plugin_class = plugin_id.rsplit('.', 1)
				Component = self.module.daemon.import_plugin(plugin_path, plugin_class)
				if Component is not None:
					self.module.components[identifier] = Component(daemon=self.module.daemon)
		for identifier in self.module.components.keys():
			self.module.components[identifier].configure(configuration, section_name)

