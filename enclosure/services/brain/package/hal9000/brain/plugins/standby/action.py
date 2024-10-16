from json import dumps as json_dumps
from datetime import time as datetime_time, \
                     datetime as datetime_datetime
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import Brain, BRAIN_STATUS
from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data, RUNLEVEL, DataInvalid, CommitPhase


class Action(HAL9000_Action):

	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'standby', action_name, plugin_status, **kwargs)
		self.daemon.plugins['standby'].runlevel = RUNLEVEL.RUNNING
		self.time_sleep = None
		self.time_wakeup = None


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.config['sleep-time']  = configuration.get('standby', 'sleep-time', fallback=None)
		self.config['wakeup-time'] = configuration.get('standby', 'wakeup-time', fallback=None)
		try:
			self.time_sleep = datetime_time.fromisoformat(self.config['sleep-time'])
		except ValueError as e:
			self.logger.error(f"[standby] failed to parse configured sleep-time '{self.config['sleep-time']}' as (ISO-8601 formatted) time")
			self.time_sleep = None
			self.time_wakeup = None
			return
		try:
			self.time_wakeup = datetime_time.fromisoformat(self.config['wakeup-time'])
		except ValueError as e:
			self.logger.error(f"[standby] failed to parse configured wakeup-time '{self.config['wakeup-time']}' as (ISO-8601 formatted) time")
			self.time_sleep = None
			self.time_wakeup = None
			return
		self.daemon.plugins['standby'].addLocalNames(['time_sleep'])
		self.daemon.plugins['standby'].addLocalNames(['time_wakeup'])
		self.daemon.plugins['standby'].time_sleep = str(self.time_sleep)
		self.daemon.plugins['standby'].time_wakeup = str(self.time_wakeup)
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')


	def runlevel(self) -> str:
		return RUNLEVEL.RUNNING


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			if new_runlevel == RUNLEVEL.RUNNING:
				if self.time_sleep is not None:
					sleep_secs = (self.time_sleep.hour * 3600) + (self.time_sleep.minute * 60)
					self.daemon.create_scheduled_signal(sleep_secs, 'brain', {'status': BRAIN_STATUS.ASLEEP},
					                                    'scheduler://brain/time:sleep', 'cron')
				if self.time_wakeup is not None:
					wakeup_secs = (self.time_wakeup.hour * 3600) + (self.time_wakeup.minute * 60)
					self.daemon.create_scheduled_signal(wakeup_secs, 'brain', {'status': BRAIN_STATUS.AWAKE},
					                                    'scheduler://brain/time:wakeup', 'cron')
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		if phase == CommitPhase.LOCAL_REQUESTED:
			if old_status == BRAIN_STATUS.LAUNCHING:
					if self.time_sleep is not None and self.time_wakeup is not None:
						next_brain_status = BRAIN_STATUS.AWAKE
						time_now = datetime_datetime.now().time()
						if self.time_sleep > self.time_wakeup:
							if time_now > self.time_sleep or time_now < self.time_wakeup:
								next_brain_status = BRAIN_STATUS.ASLEEP
						else:
							if time_now > self.time_sleep and time_now < self.time_wakeup:
								next_brain_status = BRAIN_STATUS.ASLEEP
						if next_brain_status != new_status:
							self.daemon.queue_signal('brain', {'status': next_brain_status})
							return False
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		if new_time in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			if self.daemon.plugins['brain'].runlevel == RUNLEVEL.READY:
				if new_time == Brain.TIME_SYNCHRONIZED:
					if self.time_sleep is not None and self.time_wakeup is not None:
						next_brain_status = BRAIN_STATUS.AWAKE
						time_now = datetime_datetime.now().time()
						if self.time_sleep > self.time_wakeup:
							if time_now > self.time_sleep or time_now < self.time_wakeup:
								next_brain_status = BRAIN_STATUS.ASLEEP
						else:
							if time_now > self.time_sleep and time_now < self.time_wakeup:
								next_brain_status = BRAIN_STATUS.ASLEEP
						self.daemon.queue_signal('brain', {'status': next_brain_status})
		return True

