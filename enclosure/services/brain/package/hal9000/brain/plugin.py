from __future__ import annotations
from typing import Callable as typing_Callable
from configparser import ConfigParser as configparser_ConfigParser

from aiomqtt import Message as aiomqtt_Message


class HAL9000_Plugin_Data(object):
	STATUS_UNINITIALIZED = '<uninitialized>'
	STATUS_REQUESTED = '<requested>'
	STATUS_CONFIRMED = '<confirmed>'
	SPECIAL_NAMES = ['plugin_id', 'module', 'local_names', 'remote_names', 'callbacks_data', 'callbacks_signal']

	def __init__(self, plugin_id: str, **kwargs) -> None:
		self.plugin_id = plugin_id
		self.local_names = ['runlevel', 'status']
		self.local_names.extend(kwargs.get('local_names', []))
		self.remote_names = {}
		self.remote_names.update({x: HAL9000_Plugin_Data.STATUS_UNINITIALIZED for x in kwargs.get('remote_names', [])})
		for name in self.local_names + list(self.remote_names.keys()):
			super().__setattr__(name, kwargs.get(name, HAL9000_Plugin_Data.STATUS_UNINITIALIZED))
		for name, value in kwargs.items():
			if name in self.local_names or name in self.remote_names:
				super().__setattr__(name, value)
		self.callbacks_data = { '*': set() }
		self.callbacks_signal = set()


	def addLocalNames(self, local_names: list) -> None:
		for name in local_names:
			if name not in HAL9000_Plugin_Data.SPECIAL_NAMES:
				self.local_names.append(name)
				super().__setattr__(name, HAL9000_Plugin_Data.STATUS_UNINITIALIZED)


	def addRemoteNames(self, remote_names: list) -> None:
		for name in remote_names:
			if name not in HAL9000_Plugin_Data.SPECIAL_NAMES:
				self.remote_names[name] = HAL9000_Plugin_Data.STATUS_UNINITIALIZED
				super().__setattr__(name, HAL9000_Plugin_Data.STATUS_UNINITIALIZED)


	def delLocalNames(self, local_names: list) -> None:
		for name in local_names:
			if name in self.local_names:
				del self.local_names[name]
				delattr(self, name)


	def delRemoteNames(self, remote_names: list) -> None:
		for name in remote_names:
			if name in self.remote_names:
				del self.remote_names[name]
				delattr(self, name)


	def addNameCallback(self, callback: typing_Callable[[str, str, str, bool], bool], name: str = '*') -> None:
		if name not in self.callbacks_data:
			self.callbacks_data[name] = set()
		self.callbacks_data[name].add(callback)


	def delNameCallback(self, callback: typing_Callable[[str, str, str, bool], bool], name: str = '*') -> None:
		if name in self.callbacks_data:
			self.callbacks_data[name].remove(callback)


	def addSignalHandler(self, callback: typing_Callable[[HAL9000_Plugin_Data, dict], None]) -> None:
		self.callbacks_signal.add(callback)


	def delSignalHandler(self, callback: typing_Callable[[HAL9000_Plugin_Data, dict], None], name: str = '*') -> None:
		self.callbacks_signal.remove(callback)


	async def signal(self, signal: dict) -> None:
		for callback in self.callbacks_signal:
			await callback(self, signal)


	def __setattr__(self, name: str, new_value) -> None:
		if isinstance(new_value, tuple):
			if len(new_value) != 2:
				raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): valid tuples must be a value as the 1st item and " \
				                f"either HAL9000_Plugin_Data.STATUS_REQUESTED or HAL9000_Plugin_Data.STATUS_CONFIRMED as the 2nd item")
			if name not in self.remote_names.keys():
				raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): '{name}' is not a remote item")
			match new_value[1]:
				case HAL9000_Plugin_Data.STATUS_REQUESTED:
					self.remote_names[name] = getattr(self, name)
				case HAL9000_Plugin_Data.STATUS_CONFIRMED:
					self.remote_names[name] = new_value[0]
			new_value = new_value[0]
		if name in HAL9000_Plugin_Data.SPECIAL_NAMES:
			super().__setattr__(name, new_value)
			return
		if name not in self.local_names and name not in self.remote_names:
			raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): '{name}' is not a registered attribute name")
		old_value = None
		if hasattr(self, name) is True:
			old_value = getattr(self, name)
		if new_value is None:
			new_value = HAL9000_Plugin_Data.STATUS_UNINITIALIZED
		if old_value != new_value:
			pending = False
			if name in self.remote_names.keys():
				if new_value != self.remote_names[name]:
					pending = True
			commit_value = True
			for callback_name in ['*', name]:
				if callback_name in self.callbacks_data:
					for callback in self.callbacks_data[callback_name]:
						result = callback(self, name, old_value, new_value, pending)
						if pending is False and result is None:
							raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): a registerd callback " \
							                f"returned <None> instead of a boolean value (BUG!) => {callback}")
						commit_value &= result
			if pending is True:
				self.remote_names[name] = new_value
			elif commit_value is True:
				super().__setattr__(name, new_value)


	def __repr__(self) -> str:
		result = '{'
		for name in self.local_names:
			value = getattr(self, name)
			if value != HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
				result += f'{name}=\'{value}\', '
		for name, pending_value in self.remote_names.items():
			value = getattr(self, name)
			if value == pending_value:
				result += f'{name}=\'{value}\', '
			else:
				result += f'{name}=\'{value}\' (pending \'{pending_value}\'), '
		if len(result) > 2:
			result = result[:-2]
		result += '}'
		return result


class HAL9000_Plugin(object):
	RUNLEVEL_UNKNOWN  = "unknown"
	RUNLEVEL_STARTING = "starting"
	RUNLEVEL_READY    = "ready"
	RUNLEVEL_RUNNING  = "running"
	RUNLEVEL_KILLED   = "killed"

	def __init__(self, plugin_type: str, plugin_class: str, plugin_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		self.name = f"{plugin_type}:{plugin_class}:{plugin_name}"
		self.daemon = kwargs.get('daemon', None)
		if plugin_status is not None and self.daemon is not None:
			if plugin_class not in self.daemon.plugins:
				self.daemon.plugins[plugin_class] = plugin_status
		self.config = {}

	def __repr__(self) -> str:
		return self.name


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		pass


	def runlevel(self) -> str:
		return HAL9000_Plugin.RUNLEVEL_UNKNOWN


	def runlevel_error(self) -> dict:
		return {'id': '911',
		        'level': 'error',
		        'title': "BUG: HAL9000_Plugin derived class did not implement runlevel_error()"}



class HAL9000_Action(HAL9000_Plugin):
	def __init__(self, action_class: str, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Plugin.__init__(self, "action", action_class, action_name, plugin_status, **kwargs)


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name)



class HAL9000_Trigger(HAL9000_Plugin):
	def __init__(self, trigger_class: str, trigger_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Plugin.__init__(self, "trigger", trigger_class, trigger_name, plugin_status, **kwargs)
		self.sleepless = False


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name)
		self.sleepless = configuration.getboolean(section_name, 'sleepless', fallback=False)


	def runlevel(self) -> str:
		return HAL9000_Plugin.RUNLEVEL_RUNNING


	def handle(self, data: aiomqtt_Message) -> dict:
		return {}

