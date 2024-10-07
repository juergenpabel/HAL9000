from json import dumps as json_dumps
from datetime import datetime as datetime_datetime
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data, CommitPhase


class Action(HAL9000_Action):

	STATUS_WAITING_READY =   'waiting:ready'
	STATUS_WAITING_RUNNING = 'waiting:running'
	STATUS_WAITING_WELCOME = 'waiting:welcome'
	STATUS_FINISHED        = 'finished'

	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'startup', action_name, plugin_status, **kwargs)
		self.daemon.plugins['startup'].status = Action.STATUS_WAITING_READY
		self.waiting_welcome_conditions = []

	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.config['require-synced-time'] = configuration.getboolean('startup', 'require-synced-time', fallback=False)
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_runlevel_callback, 'runlevel')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_status_callback, 'status')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')


	def runlevel(self) -> str:
		return HAL9000_Plugin.RUNLEVEL_RUNNING


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING:
					if 'timesync' not in self.waiting_welcome_conditions:
						if self.config['require-synced-time'] is True and self.daemon.plugins['brain'].time != 'synchronized':
							self.daemon.logger.info(f"[startup] inhibiting change of runlevel from '{old_runlevel}' to '{new_runlevel}' due to not-yet-synchronized time")
							self.waiting_welcome_conditions.append('timesync')
					if 'frontend' not in self.waiting_welcome_conditions:
						if self.daemon.plugins['frontend'].status != 'online':
							self.daemon.logger.info(f"[startup] inhibiting change of runlevel from '{old_runlevel}' to '{new_runlevel}' due to not-yet-online frontend")
							self.waiting_welcome_conditions.append('frontend')
					if len(self.waiting_welcome_conditions) > 0:
						self.daemon.logger.info(f"[startup] inhibiting change of runlevel from '{old_runlevel}' to '{new_runlevel}' due to unmet conditions: " \
						                        f"{self.waiting_welcome_conditions}")
						return False
			case CommitPhase.COMMIT:
				match new_runlevel:
					case HAL9000_Plugin.RUNLEVEL_READY:
						self.daemon.plugins['startup'].status = Action.STATUS_WAITING_RUNNING
					case HAL9000_Plugin.RUNLEVEL_RUNNING:
						self.daemon.plugins['startup'].status = Action.STATUS_WAITING_WELCOME
						if self.daemon.plugins['frontend'].screen == 'animations:system-starting':
							self.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop', 'value': 'false'}}})
							self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.COMMIT:
				if self.daemon.plugins['startup'].status == Action.STATUS_WAITING_WELCOME:
					datetime_now = datetime_datetime.now()
					epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
					synced = True if self.daemon.plugins['brain'].time == 'synchronized' else False
					self.daemon.queue_signal('mqtt', {'topic': 'hal9000/command/frontend/system/features', 'payload': {'time': {'epoch': epoch, 'synced': synced, 'src': 'startup:on_brain_status'}}})
					match new_status:
						case Daemon.BRAIN_STATUS_AWAKE:
							self.daemon.queue_signal('mqtt', {'topic': 'hal9000/command/frontend/gui/screen', 'payload': {'on': {'src': 'startup:on_brain_status'}}})
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
							self.daemon.create_scheduled_signal(1.5, 'kalliope', {'command': {'name': 'welcome', 'parameter': None}},
								                                    'scheduler://kalliope/welcome:delay)')
						case Daemon.BRAIN_STATUS_ASLEEP:
							self.daemon.queue_signal('kalliope', {'status': 'sleeping'})
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {'src': 'startup:on_brain_status'}}}})
							self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {'src': 'startup:on_brain_status'}}}})
							self.daemon.queue_signal('mqtt', {'topic': 'hal9000/command/frontend/gui/screen', 'payload': {'off': {'src': 'startup:on_brain_status'}}})
					self.daemon.plugins['startup'].status = Action.STATUS_FINISHED
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.COMMIT:
				if 'timesync' in self.waiting_welcome_conditions and new_time == 'synchronized':
					self.waiting_welcome_conditions.remove('timesync')
					if len(self.waiting_welcome_conditions) == 0:
						self.daemon.queue_signal('brain', {'runlevel': HAL9000_Plugin.RUNLEVEL_RUNNING})
		return True


	def on_frontend_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		return True


	def on_frontend_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.COMMIT:
				if 'frontend' in self.waiting_welcome_conditions and new_status == 'online':
					self.waiting_welcome_conditions.remove('frontend')
					if len(self.waiting_welcome_conditions) == 0:
						self.daemon.queue_signal('brain', {'runlevel': HAL9000_Plugin.RUNLEVEL_RUNNING})
		return True


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_screen: str, new_screen: str, phase: CommitPhase) -> bool:
		return True

 
	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		return True


