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
		self.addLocalNames(['time'])
		self.time = DataInvalid.UNKNOWN, CommitPhase.COMMIT
		self.runlevel = RUNLEVEL.STARTING, CommitPhase.COMMIT
		self.status = STATUS.LAUNCHING, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.addSignalHandler(self.on_brain_signal)
		self.addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.addNameCallback(self.on_brain_status_callback, 'status')
		self.addNameCallback(self.on_brain_time_callback, 'time')
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.SYNCING, 'brain: brain.time==unknown', self.runlevel_inhibitor_syncing_time)


	async def runlevel_inhibitor_syncing_time(self) -> bool:
		if self.time in list(DataInvalid):
			return False
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin, signal: dict) -> None:
		if 'runlevel' in signal:
			match self.runlevel:
				case RUNLEVEL.STARTING | RUNLEVEL.SYNCING | RUNLEVEL.PREPARING:
					self.runlevel = signal['runlevel']
				case RUNLEVEL.RUNNING:
					self.module.daemon.logger.error(f"[brain] signal with unexpected new runlevel '{signal['runlevel']}' " \
					                                f"(current runlevel='{RUNLEVEL.RUNNING}')")
				case other:
					self.module.daemon.logger.error(f"[brain] unexpected current runlevel '{self.runlevel}'")
		if 'status' in signal:
			match self.status:
				case STATUS.LAUNCHING | STATUS.AWAKE | STATUS.ASLEEP:
					self.status = signal['status']
				case STATUS.DYING:
					pass
		if 'time' in signal:
			match os_path_exists('/run/systemd/timesync/synchronized'):
				case True:
					self.time = Action.TIME_SYNCHRONIZED
				case False:
					self.time = Action.TIME_UNSYNCHRONIZED


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				match old_runlevel:
					case RUNLEVEL.STARTING:
						if new_runlevel != RUNLEVEL.SYNCING:
							self.module.daemon.logger.info(f"[brain] preventing (invalid) change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
							return False
					case RUNLEVEL.SYNCING:
						if new_runlevel != RUNLEVEL.PREPARING:
							self.module.daemon.logger.info(f"[brain] preventing (invalid) change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
							return False
					case RUNLEVEL.PREPARING:
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
						self.module.daemon.create_scheduled_signal(   1, 'brain', {'time': {}}, 'scheduler://brain/time', 'interval')
					case Action.TIME_SYNCHRONIZED:
						self.module.daemon.create_scheduled_signal(3600, 'brain', {'time': {}}, 'scheduler://brain/time', 'interval')
		return True

