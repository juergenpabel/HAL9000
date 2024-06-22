#!/usr/bin/python3

from configparser import ConfigParser
from hal9000.daemon.plugin import HAL9000_Plugin


class HAL9000_Module(HAL9000_Plugin):
	MODULE_RUNLEVEL_UNKNOWN  = "unknown"
	MODULE_RUNLEVEL_STARTING = "starting"
	MODULE_RUNLEVEL_RUNNING  = "running"
	MODULE_RUNLEVEL_HALTING  = "halting"

	def __init__(self, module_type: str, module_class: str, module_name: str, **kwargs) -> None:
		HAL9000_Plugin.__init__(self, f"{module_type}:{module_class}:{module_name}")
		self.daemon = kwargs.get('daemon', None)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name)


	def runlevel(self, cortex: dict) -> str:
		return HAL9000_Module.MODULE_RUNLEVEL_UNKNOWN


	def runlevel_error(self, cortex: dict) -> dict:
		return {"code": "TODO",
		        "level": "error",
		        "message": "BUG: HAL9000_Module derived class did not implement runlevel_error()"}


class HAL9000_Action(HAL9000_Module):
	def __init__(self, action_class: str, action_name: str, **kwargs) -> None:
		HAL9000_Module.__init__(self, "action", action_class, action_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict = None) -> None:
		HAL9000_Module.configure(self, configuration, section_name, cortex)


	def process(self, signal: dict, cortex: dict) -> None:
		pass


class HAL9000_Trigger(HAL9000_Module):
	def __init__(self, trigger_class: str, trigger_name: str, **kwargs) -> None:
		HAL9000_Module.__init__(self, "trigger", trigger_class, trigger_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		HAL9000_Module.configure(self, configuration, section_name, None)


	def runlevel(self, cortex: dict) -> str:
		return HAL9000_Module.MODULE_RUNLEVEL_RUNNING


	def handle(self, message) -> dict:
		return None

