from enum import StrEnum as enum_StrEnum
from json import dumps as json_dumps
from datetime import datetime as datetime_datetime
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import BRAIN_STATUS
from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data, RUNLEVEL, CommitPhase


class STARTUP_STATUS(enum_StrEnum):
	WAITING_READY   = 'waiting:ready'
	WAITING_RUNNING = 'waiting:running'
	WAITING_WELCOME = 'waiting:welcome'
	FINISHED        = 'finished'


class Action(HAL9000_Action):

	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'startup', action_name, plugin_status, **kwargs)
		self.daemon.plugins['startup'].status = STARTUP_STATUS.WAITING_READY


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.config['timeout-starting'] = configuration.getint('startup', 'timeout-starting', fallback=0)
		self.config['require-synced-time'] = configuration.getboolean('startup', 'require-synced-time', fallback=False)
		self.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'startup:brain_time',       self.runlevel_inhibitor_ready_brain_time)
		self.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'startup:frontend_status',  self.runlevel_inhibitor_ready_frontend_status)
		self.daemon.plugins['startup'].addSignalHandler(self.on_startup_signal)
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		if self.config['timeout-starting'] > 0:
			self.daemon.create_scheduled_signal(self.config['timeout-starting'], 'startup', {'timeout': 'starting'}, 'scheduler://startup/timeout:starting')


	def runlevel(self) -> str:
		return RUNLEVEL.RUNNING


	def runlevel_inhibitor_ready_brain_time(self) -> bool:
		if self.config['require-synced-time'] is True and self.daemon.plugins['brain'].time != 'synchronized':
			return False
		return True


	def runlevel_inhibitor_ready_frontend_status(self) -> bool:
		if self.daemon.plugins['frontend'].status != 'online':
			return False
		return True


	async def on_startup_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'timeout' in signal and signal['timeout'] == 'starting':
			starting_plugins = list(self.daemon.triggers.values()) + list(self.daemon.actions.values())
			starting_plugins = list(filter(lambda plugin: plugin.runlevel() != RUNLEVEL.RUNNING, starting_plugins))
			if len(starting_plugins) > 0:
				self.daemon.logger.critical(f"[startup] Startup failed (plugins that haven't reached runlevel 'running' before startup timeout):")
				for plugin in starting_plugins:
					plugin_type, plugin_class, plugin_instance = str(plugin).split(':', 2)
					error = plugin.runlevel_error()
					self.daemon.logger.critical(f"[startup] - Plugin '{plugin_class}' (instance='{plugin_instance}')")
					self.daemon.process_error('critical', error['id'], f"    Plugin '{plugin_class}'", error['title'])
				self.daemon.logger.debug(f"[startup] STATUS at startup-timeout = { {k: v for k,v in self.daemon.plugins.items() if v.hidden is False} }")
				self.daemon.plugins['brain'].status = BRAIN_STATUS.DYING


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.COMMIT:
				match new_runlevel:
					case RUNLEVEL.READY:
						self.daemon.remove_scheduled_signal('scheduler://startup/timeout:starting')
						self.daemon.plugins['startup'].status = STARTUP_STATUS.WAITING_RUNNING
					case RUNLEVEL.RUNNING:
						self.daemon.plugins['startup'].status = STARTUP_STATUS.WAITING_WELCOME
						if self.daemon.plugins['frontend'].screen == 'animations:system-starting':
							self.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop', 'value': 'false'}}})
							self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
							#TODO: re-submit or inhibit ?
						else:
							datetime_now = datetime_datetime.now()
							epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
							synced = True if self.daemon.plugins['brain'].time == 'synchronized' else False
							self.daemon.queue_signal('mqtt', {'topic': 'hal9000/command/frontend/system/features',
							                                  'payload': {'time': {'epoch': epoch, 'synced': synced}}})
							match self.daemon.plugins['brain'].status:
								case BRAIN_STATUS.AWAKE:
									self.daemon.queue_signal('mqtt', {'topic': 'hal9000/command/frontend/gui/screen', 'payload': {'on': {}}})
									self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
									self.daemon.create_scheduled_signal(1.5, 'kalliope', {'command': {'name': 'welcome', 'parameter': {}}},
										                                    'scheduler://kalliope/welcome:delay)')
								case BRAIN_STATUS.ASLEEP:
									self.daemon.queue_signal('kalliope', {'status': 'sleeping'})
									self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
									self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
									self.daemon.queue_signal('mqtt', {'topic': 'hal9000/command/frontend/gui/screen', 'payload': {'off': {}}})
							self.daemon.plugins['startup'].status = STARTUP_STATUS.FINISHED
							self.daemon.plugins['startup'].hidden = True
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.COMMIT:
				if self.daemon.plugins['startup'].status == STARTUP_STATUS.WAITING_WELCOME:
					match new_status:
						case BRAIN_STATUS.AWAKE:
							self.daemon.queue_signal('mqtt', {'topic': 'hal9000/command/frontend/gui/screen', 'payload': {'on': {}}})
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
							self.daemon.create_scheduled_signal(1.5, 'kalliope', {'command': {'name': 'welcome', 'parameter': {}}},
								                                    'scheduler://kalliope/welcome:delay)')
						case BRAIN_STATUS.ASLEEP:
							self.daemon.queue_signal('kalliope', {'status': 'sleeping'})
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
							self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
							self.daemon.queue_signal('mqtt', {'topic': 'hal9000/command/frontend/gui/screen', 'payload': {'off': {}}})
					self.daemon.plugins['startup'].status = STARTUP_STATUS.FINISHED
					self.daemon.plugins['startup'].hidden = True
		return True


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_screen: str, new_screen: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if self.daemon.plugins['brain'].runlevel == RUNLEVEL.READY:
					if new_screen == 'idle':
						return False
		return True

