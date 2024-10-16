from __future__ import annotations
from enum import Enum as enum_Enum, \
                 StrEnum as enum_StrEnum
from typing import Callable as typing_Callable
from configparser import ConfigParser as configparser_ConfigParser
from logging import getLogger as logging_getLogger
from aiomqtt import Message as aiomqtt_Message


class CommitPhase(enum_Enum):
	LOCAL_REQUESTED = 0
	REMOTE_REQUESTED = 1
	COMMIT = 2


class DataInvalid(enum_StrEnum):
	UNINITIALIZED = '<uninitialized>'
	UNKNOWN       = '<unknown>'


class HAL9000_Plugin_Data(object):
	SPECIAL_NAMES = ['daemon', 'plugin_id', 'module', 'hidden', 'local_names', 'remote_names', 'callbacks_data', 'callbacks_signal']

	def __init__(self, plugin_id: str, **kwargs) -> None:
		self.plugin_id = plugin_id
		self.daemon = kwargs.get('daemon', None)
		if self.daemon is None:
			self.daemon = object()
			self.daemon.logger = logging_getLogger()
		self.hidden = kwargs.get('hidden', False)
		self.local_names = ['runlevel', 'status']
		self.local_names.extend(kwargs.get('local_names', []))
		self.remote_names = {}
		self.remote_names.update({x: DataInvalid.UNINITIALIZED for x in kwargs.get('remote_names', [])})
		for name in self.local_names + list(self.remote_names.keys()):
			super().__setattr__(name, kwargs.get(name, DataInvalid.UNINITIALIZED))
		for name, value in kwargs.items():
			if name in self.local_names or name in self.remote_names:
				super().__setattr__(name, value)
		self.callbacks_data = {'*': set()}
		self.callbacks_signal = set()


	def addLocalNames(self, local_names: list) -> None:
		for name in local_names:
			if name not in HAL9000_Plugin_Data.SPECIAL_NAMES:
				self.local_names.append(name)
				super().__setattr__(name, DataInvalid.UNINITIALIZED)


	def addRemoteNames(self, remote_names: list) -> None:
		for name in remote_names:
			if name not in HAL9000_Plugin_Data.SPECIAL_NAMES:
				self.remote_names[name] = DataInvalid.UNINITIALIZED
				super().__setattr__(name, DataInvalid.UNINITIALIZED)


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


	def getRemotePendingValue(self, name: str) -> str:
		if name in self.remote_names:
			if getattr(self, name) != self.remote_names[name]:
				return self.remote_names[name]
		return None


	def __setattr__(self, name: str, new_value) -> None:
		if name in HAL9000_Plugin_Data.SPECIAL_NAMES:
			super().__setattr__(name, new_value)
			return
		if name not in self.local_names and name not in self.remote_names:
			raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): '{name}' is not a registered attribute name")
		commit_phase = CommitPhase.LOCAL_REQUESTED
		if name in self.remote_names:
			if new_value == self.remote_names[name]:
				commit_phase = CommitPhase.COMMIT
		if isinstance(new_value, tuple) is True:
			if len(new_value) != 2:
				raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): valid tuples must be a value as the 1st item and " \
				                f"either CommitPhase.REMOTE_REQUESTED or CommitPhase.COMMIT as the 2nd item")
			if new_value[1] not in CommitPhase:
				raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): 2nd item of tuple must be of enum CommitPhase")
			commit_phase = new_value[1]
			new_value = new_value[0]
		old_value = DataInvalid.UNINITIALIZED
		if hasattr(self, name) is True:
			old_value = getattr(self, name)
		if new_value is None:
			new_value = DataInvalid.UNINITIALIZED
		if old_value != new_value:
			if commit_phase == CommitPhase.LOCAL_REQUESTED:
				commit_value = True
				for callback_name in ['*', name]:
					if callback_name in self.callbacks_data:
						for callback in self.callbacks_data[callback_name]:
							result = callback(self, name, old_value, new_value, CommitPhase.LOCAL_REQUESTED)
							if result is None:
								raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): a registerd callback " \
								                f"returned <None> instead of a boolean value (BUG!) => {callback}")
							if result is False:
								from hal9000.brain.daemon import Brain # late import due to partially initialized module (circular imports)
								self.daemon.logger.log(Brain.LOGLEVEL_TRACE, f"[{self.plugin_id}] callback '{callback.__self__.name}" \
								                                             f"<{callback.__func__.__name__}>' declined change of " \
								                                             f"{name} from '{old_value}' to '{new_value}'")
							commit_value &= result
				if commit_value is True:
					commit_phase = CommitPhase.COMMIT if name not in self.remote_names else CommitPhase.REMOTE_REQUESTED
			if commit_phase == CommitPhase.REMOTE_REQUESTED:
				if name in self.remote_names:
					self.remote_names[name] = new_value
					for callback_name in ['*', name]:
						if callback_name in self.callbacks_data:
							for callback in self.callbacks_data[callback_name]:
								callback(self, name, old_value, new_value, CommitPhase.REMOTE_REQUESTED)
			if commit_phase == CommitPhase.COMMIT:
				super().__setattr__(name, new_value)
				if name in self.remote_names:
					self.remote_names[name] = new_value
				for callback_name in ['*', name]:
					if callback_name in self.callbacks_data:
						for callback in self.callbacks_data[callback_name]:
							callback(self, name, old_value, new_value, CommitPhase.COMMIT)


	def __repr__(self) -> str:
		result = '{'
		for name in self.local_names:
			value = getattr(self, name)
			if value != DataInvalid.UNINITIALIZED:
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


class RUNLEVEL(enum_StrEnum):
	STARTING = "starting"
	READY    = "ready"
	RUNNING  = "running"
	KILLED   = "killed"


class HAL9000_Plugin(object):

	def __init__(self, plugin_type: str, plugin_class: str, plugin_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		self.name = f"{plugin_type}:{plugin_class}:{plugin_name if plugin_name != plugin_class else 'default'}"
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
		return DataInvalid.UNKNOWN


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
		return RUNLEVEL.RUNNING


	def handle(self, data: aiomqtt_Message) -> dict:
		return {}

