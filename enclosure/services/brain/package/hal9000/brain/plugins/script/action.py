from os import system as os_system
from os.path import exists as os_path_exists
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data, RUNLEVEL


class Action(HAL9000_Action):
	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'script', action_name, plugin_status, **kwargs)
		self.daemon.plugins['script'].runlevel = RUNLEVEL.RUNNING
		plugin_status.hidden = True
		self.scripts = {}


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		for option_name in configuration.options(section_name):
			if option_name != 'plugin':
				script_path = configuration.getstring(section_name, option_name, fallback=None)
				if script_path is not None:
					match os_path_exists(script_path):
						case True:
							self.scripts[option_name] = script_path
						case False:
							self.daemon.logger.error(f"[action:script] script '{script_path}' (id '{option_name}') not found, skipping")
		self.daemon.plugins['script'].addSignalHandler(self.on_script_signal)


	def runlevel(self) -> str:
		return RUNLEVEL.RUNNING


	async def on_script_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'id' in signal:
			script_id = signal['id']
			if script_id not in self.scripts:
				self.daemon.logger.warning(f"[action:script] ignoring signal with unknown script id '{script_id}'")
				return
			self.daemon.logger.info(f"[action:script] Executing configured script with id '{script_id}': {self.scripts[script_id]}")
			os_system(self.scripts[script_id])

