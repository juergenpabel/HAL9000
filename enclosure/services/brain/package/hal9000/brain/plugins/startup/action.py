from enum import StrEnum as enum_StrEnum
from json import dumps as json_dumps
from datetime import datetime as datetime_datetime
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import BRAIN_STATUS
from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data, RUNLEVEL, DataInvalid, CommitPhase


class STARTUP_STATUS(enum_StrEnum):
	WAITING_READY   = 'waiting:ready'
	WAITING_RUNNING = 'waiting:running'
	WAITING_WELCOME = 'waiting:welcome'
	FINISHED        = 'finished'


class Action(HAL9000_Action):

	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'startup', action_name, plugin_status, **kwargs)
		self.daemon.plugins['startup'].runlevel = RUNLEVEL.RUNNING
		self.daemon.plugins['startup'].status = STARTUP_STATUS.WAITING_READY
		self.daemon.plugins['startup'].hidden = True


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.config['timeout-starting'] = configuration.getint('startup', 'timeout-starting', fallback=0)
		self.config['require-synced-time'] = configuration.getboolean('startup', 'require-synced-time', fallback=False)
		self.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'startup:brain_time',       self.runlevel_inhibitor_ready_brain_time)
		self.daemon.plugins['startup'].addSignalHandler(self.on_startup_signal)
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		if self.config['timeout-starting'] > 0:
			self.daemon.create_scheduled_signal(self.config['timeout-starting'], 'startup', {'timeout': 'starting'}, 'scheduler://startup/timeout:starting')


	def runlevel_inhibitor_ready_brain_time(self) -> bool:
		if self.config['require-synced-time'] is True and self.daemon.plugins['brain'].time != 'synchronized':
			return False
		return True


	async def on_startup_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'welcome' in signal:
			self.startup_welcome()
		if 'timeout' in signal:
			if signal['timeout'] == 'starting' and self.daemon.plugins['brain'].runlevel == RUNLEVEL.STARTING:
				starting_plugins = list(filter(lambda plugin: plugin.name != 'brain' and plugin.runlevel != RUNLEVEL.RUNNING, self.daemon.plugins.values()))
				if len(starting_plugins) > 0:
					self.daemon.logger.critical(f"[startup] Startup failed (plugins that haven't reached runlevel 'running' before startup timeout):")
					for plugin in starting_plugins:
						self.daemon.logger.critical(f"[startup] - Plugin '{plugin.name}'")
				self.daemon.logger.debug(f"[startup] STATUS at startup-timeout = { {k: v for k,v in self.daemon.plugins.items() if v.hidden is False} }")
				self.daemon.plugins['brain'].status = BRAIN_STATUS.DYING, CommitPhase.COMMIT


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.COMMIT:
				match new_runlevel:
					case RUNLEVEL.READY:
						self.daemon.plugins['startup'].status = STARTUP_STATUS.WAITING_RUNNING
						self.daemon.remove_scheduled_signal('scheduler://startup/timeout:starting')
					case RUNLEVEL.RUNNING:
						self.daemon.plugins['startup'].status = STARTUP_STATUS.WAITING_WELCOME
						if self.daemon.plugins['frontend'].screen.split(':', 1).pop(0) != 'animations':
							self.daemon.queue_signal('startup', {'welcome': {}})
						else:
							self.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop',
							                                                              'value': 'false'}}})
		return True


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_screen: str, new_screen: str, phase: CommitPhase) -> bool:
		if new_screen in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_screen == 'idle':
					if self.daemon.plugins['brain'].runlevel == RUNLEVEL.READY:
						return False
			case CommitPhase.COMMIT:
				match new_screen:
					case 'none':
						if self.daemon.plugins['startup'].status == STARTUP_STATUS.WAITING_WELCOME:
							self.daemon.queue_signal('startup', {'welcome': {}})
					case other:
						if self.daemon.plugins['startup'].status == STARTUP_STATUS.WAITING_WELCOME:
							self.daemon.logger.warn(f"[startup] an unexpected screen '{new_screen}' is to be set, cancelling startup/welcome")
							self.daemon.plugins['startup'].status = STARTUP_STATUS.FINISHED
		return True


	def startup_welcome(self) -> None:
		match self.daemon.plugins['brain'].status:
			case BRAIN_STATUS.AWAKE:
				self.daemon.logger.info(f"[startup] now running welcome message")
				self.daemon.queue_signal('frontend', {'features': {'display': {'backlight': True}}})
				self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
				self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
				self.daemon.create_scheduled_signal(1.5, 'kalliope', {'command': {'name': 'welcome', 'parameter': {}}},
					                                    'scheduler://kalliope/welcome:delay)')
			case BRAIN_STATUS.ASLEEP:
				self.daemon.logger.info(f"[startup] skipping welcome message (system is currently in sleep mode)")
				self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
				self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
				self.daemon.queue_signal('frontend', {'features': {'display': {'backlight': False}}})
				self.daemon.queue_signal('kalliope', {'status': 'sleeping'})
		self.daemon.plugins['startup'].status = STARTUP_STATUS.FINISHED
