from json import dumps as json_dumps
from datetime import time as datetime_time, \
                     datetime as datetime_datetime
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, RUNLEVEL, DataInvalid, CommitPhase
from hal9000.brain.plugins.brain import Action as Brain, STATUS as BRAIN_STATUS


class Action(HAL9000_Action):

	def __init__(self, action_instance: str, **kwargs) -> None:
		super().__init__('standby', **kwargs)
		self.module.hidden = True
		self.addLocalNames(['time_sleep'])
		self.addLocalNames(['time_wakeup'])
		self.runlevel = RUNLEVEL.RUNNING, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.config['sleep-time']  = configuration.get('standby', 'sleep-time', fallback=None)
		self.module.config['wakeup-time'] = configuration.get('standby', 'wakeup-time', fallback=None)
		try:
			self.time_sleep = datetime_time.fromisoformat(self.module.config['sleep-time'])
		except ValueError as e:
			self.module.daemon.logger.error(f"[standby] failed to parse configured sleep-time '{self.module.config['sleep-time']}' " \
			                                f"as (ISO-8601 formatted) time")
			self.time_sleep = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
			self.time_wakeup = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
			return
		try:
			self.time_wakeup = datetime_time.fromisoformat(self.module.config['wakeup-time'])
		except ValueError as e:
			self.module.daemon.logger.error(f"[standby] failed to parse configured wakeup-time '{self.module.config['wakeup-time']}' " \
			                                f"as (ISO-8601 formatted) time")
			self.time_sleep = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
			self.time_wakeup = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
			return
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			match new_runlevel:
				case RUNLEVEL.SYNCING:
					self.module.hidden = False
				case RUNLEVEL.RUNNING:
					if self.time_sleep != DataInvalid.UNINITIALIZED:
						sleep_secs = (self.time_sleep.hour * 3600) + (self.time_sleep.minute * 60)
						self.module.daemon.create_scheduled_signal(sleep_secs, 'brain', {'status': str(BRAIN_STATUS.ASLEEP)}, \
						                                           'scheduler://brain/time:sleep', 'cron')
					if self.time_wakeup != DataInvalid.UNINITIALIZED:
						wakeup_secs = (self.time_wakeup.hour * 3600) + (self.time_wakeup.minute * 60)
						self.module.daemon.create_scheduled_signal(wakeup_secs, 'brain', {'status': str(BRAIN_STATUS.AWAKE)}, \
						                                           'scheduler://brain/time:wakeup', 'cron')
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		if phase == CommitPhase.LOCAL_REQUESTED:
			if old_status == BRAIN_STATUS.LAUNCHING and new_status != BRAIN_STATUS.DYING:
				if self.time_sleep not in list(DataInvalid) and self.time_wakeup not in list(DataInvalid):
					next_brain_status = BRAIN_STATUS.AWAKE
					time_now = datetime_datetime.now().time()
					if self.time_sleep > self.time_wakeup:
						if time_now > self.time_sleep or time_now < self.time_wakeup:
							next_brain_status = BRAIN_STATUS.ASLEEP
					else:
						if time_now > self.time_sleep and time_now < self.time_wakeup:
							next_brain_status = BRAIN_STATUS.ASLEEP
					if next_brain_status != new_status:
						self.module.daemon.queue_signal('brain', {'status': next_brain_status})
						return False
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		if new_time in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			if self.module.daemon.plugins['brain'].runlevel == RUNLEVEL.SYNCING:
				if new_time == Brain.TIME_SYNCHRONIZED:
					if self.time_sleep != DataInvalid.UNINITIALIZED and self.time_wakeup != DataInvalid.UNINITIALIZED:
						next_brain_status = BRAIN_STATUS.AWAKE
						time_now = datetime_datetime.now().time()
						if self.time_sleep > self.time_wakeup:
							if time_now > self.time_sleep or time_now < self.time_wakeup:
								next_brain_status = BRAIN_STATUS.ASLEEP
						else:
							if time_now > self.time_sleep and time_now < self.time_wakeup:
								next_brain_status = BRAIN_STATUS.ASLEEP
						self.module.daemon.queue_signal('brain', {'status': str(next_brain_status)})
		return True

