from __future__ import annotations
from enum import Enum as enum_Enum, \
                 StrEnum as enum_StrEnum
from typing import Callable as typing_Callable
from configparser import ConfigParser as configparser_ConfigParser
from logging import getLogger as logging_getLogger
from aiomqtt import Message as aiomqtt_Message


class RUNLEVEL(enum_StrEnum):
	STARTING  = "starting"
	SYNCING   = "syncing"
	PREPARING = "preparing"
	RUNNING   = "running"
	KILLED    = "killed"


class CommitPhase(enum_Enum):
	LOCAL_REQUESTED = 0
	REMOTE_REQUESTED = 1
	COMMIT = 2


class DataInvalid(enum_StrEnum):
	UNINITIALIZED = '<uninitialized>'
	UNKNOWN       = '<unknown>'


class SPECIAL_NAMES(enum_StrEnum):
	DATA = 'module'
	LOCALS = 'locals'
	REMOTES = 'remotes'
	CALLBACKS_NAME = 'callbacks_name'
	CALLBACKS_SIGNAL = 'callbacks_signal'


class HAL9000_Plugin_Module(object):
	pass


class HAL9000_Plugin(object):

	def __init__(self, id: str, **kwargs) -> None:
		self.module = HAL9000_Plugin_Module()
		self.module.id = id
		self.module.hidden = kwargs.get('hidden', False)
		self.module.daemon = kwargs.get('daemon')
		self.module.daemon.plugins[id.split(':',2).pop(1) if id.endswith(':default') else id.split(':',2).pop(0)] = self
		self.module.locals = ['runlevel', 'status']
		self.module.locals.extend(kwargs.get('locals', []))
		self.module.remotes = {}
		self.module.remotes.update({x: DataInvalid.UNINITIALIZED for x in kwargs.get('remotes', [])})
		for name in self.module.locals + list(self.module.remotes.keys()):
			super().__setattr__(name, kwargs.get(name, DataInvalid.UNINITIALIZED))
		for name, value in kwargs.items():
			if name in self.module.locals or name in self.module.remotes:
				super().__setattr__(name, value)
		self.module.callbacks_name = {'*': set()}
		self.module.callbacks_signal = set()


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		self.module.config = {}


	def addLocalNames(self, locals: list) -> None:
		for local in locals:
			if local not in list(SPECIAL_NAMES):
				self.module.locals.append(local)
				super().__setattr__(local, DataInvalid.UNINITIALIZED)


	def addRemoteNames(self, remotes: list) -> None:
		for remote in remotes:
			if remote not in list(SPECIAL_NAMES):
				self.module.remotes[remote] = DataInvalid.UNINITIALIZED
				super().__setattr__(remote, DataInvalid.UNINITIALIZED)


	def delLocalNames(self, locals: list) -> None:
		for local in locals:
			if local in self.module.locals:
				del self.module.locals[local]
				delattr(self, local)


	def delRemoteNames(self, remotes: list) -> None:
		for remote in remotes:
			if remote in self.module.remotes:
				del self.module.remotes[remote]
				delattr(self, remote)


	def addNameCallback(self, callback: typing_Callable[[str, str, str, bool], bool], name: str = '*') -> None:
		if name not in self.module.callbacks_name:
			self.module.callbacks_name[name] = set()
		self.module.callbacks_name[name].add(callback)


	def delNameCallback(self, callback: typing_Callable[[str, str, str, bool], bool], name: str = '*') -> None:
		if name in self.module.callbacks_name:
			self.module.callbacks_name[name].remove(callback)


	def addSignalHandler(self, callback: typing_Callable[[HAL9000_Plugin_Data, dict], None]) -> None:
		self.module.callbacks_signal.add(callback)


	def delSignalHandler(self, callback: typing_Callable[[HAL9000_Plugin_Data, dict], None], name: str = '*') -> None:
		self.module.callbacks_signal.remove(callback)


	async def signal(self, signal: dict) -> None:
		for callback in self.module.callbacks_signal:
			await callback(self, signal)


	def getRemotePendingValue(self, name: str) -> str:
		if name in self.module.remotes:
			if getattr(self, name) != self.module.remotes[name]:
				return self.module.remotes[name]
		return None


	def __setattr__(self, name: str, new_value) -> None:
		if name in list(SPECIAL_NAMES):
			super().__setattr__(name, new_value)
			return
		if name not in self.module.locals and name not in self.module.remotes:
			raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): '{name}' is not a registered attribute name")
		commit_phase = CommitPhase.LOCAL_REQUESTED
		if name in self.module.remotes:
			if new_value == self.module.remotes[name]:
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
					if callback_name in self.module.callbacks_name:
						for callback in self.module.callbacks_name[callback_name]:
							result = callback(self, name, old_value, new_value, CommitPhase.LOCAL_REQUESTED)
							if result is None:
								raise Exception(f"HAL9000_Plugin_Data.__setattr__('{name}', '{new_value}'): a registerd callback " \
								                f"returned <None> instead of a boolean value (BUG!) => {callback}")
							if result is False:
								from hal9000.brain.daemon import Daemon # late import due to partially initialized module (circular imports)
								log_func = self.module.daemon.logger.debug
								if self.module.daemon.plugins['brain'].runlevel == RUNLEVEL.RUNNING:
									log_func = self.module.daemon.logger.info
								log_func(f"[{self.module.id}] callback '{callback.__self__.module.id}<{callback.__func__.__name__}>' " \
								         f"declined change of {name} from '{old_value}' to '{new_value}'")
							commit_value &= result
				if commit_value is True:
					commit_phase = CommitPhase.COMMIT if name not in self.module.remotes else CommitPhase.REMOTE_REQUESTED
			if commit_phase == CommitPhase.REMOTE_REQUESTED:
				if name in self.module.remotes:
					self.module.remotes[name] = new_value
					for callback_name in ['*', name]:
						if callback_name in self.module.callbacks_name:
							for callback in self.module.callbacks_name[callback_name]:
								callback(self, name, old_value, new_value, CommitPhase.REMOTE_REQUESTED)
			if commit_phase == CommitPhase.COMMIT:
				super().__setattr__(name, new_value)
				if name in self.module.remotes:
					self.module.remotes[name] = new_value
				for callback_name in ['*', name]:
					if callback_name in self.module.callbacks_name:
						for callback in self.module.callbacks_name[callback_name]:
							callback(self, name, old_value, new_value, CommitPhase.COMMIT)


	def __repr__(self) -> str:
		result = []
		for name in self.module.locals:
			value = getattr(self, name)
			if value != DataInvalid.UNINITIALIZED:
				result.append(f"{name}='{value}'")
		for name, pending_value in self.module.remotes.items():
			value = getattr(self, name)
			if value == pending_value:
				if value != DataInvalid.UNINITIALIZED:
					result.append(f"{name}='{value}'")
			else:
				result.append(f"{name}='{value}' (pending '{pending_value}')")
		return f"{self.module.id}={{{', '.join(result)}}}"


class HAL9000_Action(HAL9000_Plugin):

	def __init__(self, action_class, action_name: str = 'default', **kwargs) -> None:
		super().__init__(f'action:{action_class}:{action_name}', **kwargs)
		self.module.hidden = False


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.sleepless = True



class HAL9000_Trigger(HAL9000_Plugin):

	def __init__(self, trigger_class: str, trigger_name: str, **kwargs) -> None:
		super().__init__(f'trigger:{trigger_class}:{trigger_name}', **kwargs)
		self.module.hidden = True


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.sleepless = configuration.getboolean(section_name, 'sleepless', fallback=False)


	def handle(self, module: aiomqtt_Message) -> dict:
		return {}

