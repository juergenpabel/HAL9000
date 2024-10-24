from os import system as os_system
from os.path import exists as os_path_exists
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, RUNLEVEL


class Action(HAL9000_Action):
	def __init__(self, action_instance: str, **kwargs) -> None:
		super().__init__('script', **kwargs)
		self.module.hidden = True
		self.module.daemon.plugins['script'].runlevel = RUNLEVEL.RUNNING
		self.module.scripts = {}


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		for option_name in configuration.options(section_name):
			if option_name != 'plugin':
				script_path = configuration.getstring(section_name, option_name, fallback=None)
				if script_path is not None:
					match os_path_exists(script_path):
						case True:
							self.module.scripts[option_name] = script_path
						case False:
							self.module.daemon.logger.error(f"[action:script] script '{script_path}' (id '{option_name}') not found, skipping")
		self.module.daemon.plugins['script'].addSignalHandler(self.on_script_signal)


	async def on_script_signal(self, plugin: HAL9000_Plugin, signal: dict) -> None:
		if 'id' in signal:
			script_id = signal['id']
			if script_id not in self.module.scripts:
				self.module.daemon.logger.warning(f"[action:script] ignoring signal with unknown script id '{script_id}'")
				return
			self.module.daemon.logger.info(f"[action:script] Executing configured script with id '{script_id}': {self.module.scripts[script_id]}")
			os_system(self.module.scripts[script_id])

