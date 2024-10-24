from typing import Any
from enum import StrEnum as enum_StrEnum
from os.path import exists as os_path_exists
from configparser import ConfigParser as configparser_ConfigParser
from logging import getLogger as logging_getLogger

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, RUNLEVEL, CommitPhase, DataInvalid


class STATUS(enum_StrEnum):
	LAUNCHING = 'launching'
	AWAKE     = 'awake'
	ASLEEP    = 'asleep'
	DYING     = 'dying'


class Action(HAL9000_Action):
	TIME_UNSYNCHRONIZED = 'unsynchronized'
	TIME_SYNCHRONIZED =   'synchronized'


	def __init__(self, action_instance: str, **kwargs) -> None:
		super().__init__('brain', **kwargs)
		self.module.daemon.plugins['brain'].addLocalNames(['time'])
		self.module.daemon.plugins['brain'].runlevel = RUNLEVEL.STARTING, CommitPhase.COMMIT
		self.module.daemon.plugins['brain'].status = STATUS.LAUNCHING, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.daemon.plugins['brain'].addSignalHandler(self.on_brain_signal)
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_plugin_callback, '*')
		for plugin in self.module.daemon.plugins.values(): 
			plugin.addNameCallback(self.on_plugin_callback, '*')
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'brain:ready:time', self.runlevel_inhibitor_ready_time)


	def runlevel_inhibitor_ready_time(self) -> bool:
		if self.module.daemon.plugins['brain'].time in list(DataInvalid):
			return False
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin, signal: dict) -> None:
		if 'runlevel' in signal:
			match self.module.daemon.plugins['brain'].runlevel:
				case RUNLEVEL.STARTING:
					if signal['runlevel'] == RUNLEVEL.READY:
						self.module.daemon.plugins['brain'].runlevel = RUNLEVEL.READY
				case RUNLEVEL.READY:
					if signal['runlevel'] == RUNLEVEL.RUNNING:
						self.module.daemon.plugins['brain'].runlevel = RUNLEVEL.RUNNING
				case RUNLEVEL.RUNNING:
					self.module.daemon.logger.error(f"[brain] signal with unexpected new runlevel '{signal['runlevel']}' " \
					                                f"(current runlevel='{RUNLEVEL.RUNNING}')")
				case other:
					self.module.daemon.logger.error(f"[brain] unexpected current runlevel '{self.module.daemon.plugins['brain'].runlevel}'")
		if 'status' in signal:
			match self.module.daemon.plugins['brain'].status:
				case STATUS.LAUNCHING | STATUS.AWAKE | STATUS.ASLEEP:
					if signal['status'] in [STATUS.AWAKE, STATUS.ASLEEP, STATUS.DYING]:
						self.module.daemon.plugins['brain'].status = signal['status']
				case STATUS.DYING:
					pass
		if 'time:sync' in signal:
			match os_path_exists('/run/systemd/timesync/synchronized'):
				case True:
					self.module.daemon.plugins['brain'].time = Action.TIME_SYNCHRONIZED
				case False:
					self.module.daemon.plugins['brain'].time = Action.TIME_UNSYNCHRONIZED


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				match old_runlevel:
					case RUNLEVEL.STARTING:
						if new_runlevel != RUNLEVEL.READY:
							self.module.daemon.logger.info(f"[brain] preventing (invalid) change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
							return False
					case RUNLEVEL.READY:
						if new_runlevel != RUNLEVEL.RUNNING:
							self.module.daemon.logger.info(f"[brain] preventing (invalid) change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
							return False
					case RUNLEVEL.RUNNING:
						self.module.daemon.logger.info(f"[brain] preventing (invalid) change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
						return False
			case CommitPhase.COMMIT:
				self.module.daemon.logger.debug(f"[brain] STATUS at runlevel change from '{old_runlevel}' to '{new_runlevel}': {self.module.daemon}")
				self.module.daemon.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/runlevel', 'payload': new_runlevel})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_status not in [STATUS.AWAKE, STATUS.ASLEEP, STATUS.DYING]:
					self.module.daemon.logger.info(f"[brain] inhibiting change from status '{old_status}' to '{new_status}'")
					return False
			case CommitPhase.COMMIT:
				self.module.daemon.logger.debug(f"[brain] STATUS at status change from '{old_status}' to '{new_status}': {self.module.daemon}")
				self.module.daemon.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/status', 'payload': new_status})
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_time not in [Action.TIME_UNSYNCHRONIZED, Action.TIME_SYNCHRONIZED]:
					self.module.daemon.logger.info(f"[brain] inhibiting change from time '{old_time}' to '{new_time}'")
					return False
			case CommitPhase.COMMIT:
				match new_time:
					case Action.TIME_UNSYNCHRONIZED:
						self.module.daemon.create_scheduled_signal(   1, 'brain', {'time:sync': {}}, 'scheduler://brain/time:sync', 'interval')
					case Action.TIME_SYNCHRONIZED:
						self.module.daemon.create_scheduled_signal(3600, 'brain', {'time:sync': {}}, 'scheduler://brain/time:sync', 'interval')
		return True


	def on_plugin_callback(self, plugin: HAL9000_Plugin, key: str, old_value, new_value, phase: CommitPhase) -> bool:
		log_function = logging_getLogger().info
		match self.module.daemon.plugins['brain'].runlevel:
			case RUNLEVEL.STARTING:
				log_function = logging_getLogger().debug
			case RUNLEVEL.READY:
				log_function = logging_getLogger().debug
			case RUNLEVEL.RUNNING:
				if plugin.module.hidden is True:
					log_function = logging_getLogger().debug
		match phase:
			case CommitPhase.REMOTE_REQUESTED:
				log_function(f"[brain] Plugin '{plugin.module.id}': {key} is requested to change from '{old_value}' to '{new_value}'")
			case CommitPhase.COMMIT:
				log_function(f"[brain] Plugin '{plugin.module.id}': {key} changes from '{old_value}' to '{new_value}'")
		return True


