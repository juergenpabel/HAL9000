from enum import StrEnum as enum_StrEnum
from json import dumps as json_dumps
from datetime import datetime as datetime_datetime
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, RUNLEVEL, DataInvalid, CommitPhase
from hal9000.brain.plugins.brain import Action as Brain, STATUS as BRAIN_STATUS


class STATUS(enum_StrEnum):
	WAITING_READY   = 'waiting:ready'
	WAITING_RUNNING = 'waiting:running'
	WAITING_WELCOME = 'waiting:welcome'
	FINISHED        = 'finished'


class Action(HAL9000_Action):

	def __init__(self, action_instance: str, **kwargs) -> None:
		super().__init__('startup', **kwargs)
		self.module.hidden = True


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.config['timeout-starting'] = configuration.getint('startup', 'timeout-starting', fallback=0)
		self.module.config['require-synced-time'] = configuration.getboolean('startup', 'require-synced-time', fallback=False)
		self.module.daemon.plugins['startup'].addSignalHandler(self.on_startup_signal)
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		if self.module.config['timeout-starting'] > 0:
			self.module.daemon.create_scheduled_signal(self.module.config['timeout-starting'], 'startup', {'timeout': 'starting'}, \
			                                           'scheduler://startup/timeout:starting')
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'startup:brain_time', self.runlevel_inhibitor_ready_brain_time)
		self.runlevel = RUNLEVEL.RUNNING, CommitPhase.COMMIT
		self.status = STATUS.WAITING_READY, CommitPhase.COMMIT


	def runlevel_inhibitor_ready_brain_time(self) -> bool:
		if self.module.config['require-synced-time'] is True and self.module.daemon.plugins['brain'].time != Brain.TIME_SYNCHRONIZED:
			return False
		return True


	async def on_startup_signal(self, plugin: HAL9000_Plugin, signal: dict) -> None:
		if 'welcome' in signal:
			self.startup_welcome()
		if 'timeout' in signal:
			if signal['timeout'] == 'starting' and self.module.daemon.plugins['brain'].runlevel == RUNLEVEL.STARTING:
				starting_plugins = list(filter(lambda plugin: plugin.runlevel != RUNLEVEL.RUNNING, self.module.daemon.plugins.values()))
				starting_plugins = list(filter(lambda plugin: plugin.id != 'action:brain:default', starting_plugins))
				if len(starting_plugins) > 0:
					self.module.daemon.logger.critical(f"[startup] Startup failed (plugins that haven't reached runlevel '{RUNLEVEL.RUNNING}' " \
					                                   f"before startup timeout):")
					for plugin in starting_plugins:
						self.module.daemon.logger.critical(f"[startup] - Plugin '{plugin.name}'")
				self.module.daemon.logger.debug(f"[startup] STATUS at startup-timeout = {self.module.daemon}")
				self.module.daemon.plugins['brain'].status = BRAIN_STATUS.DYING, CommitPhase.COMMIT


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.COMMIT:
				match new_runlevel:
					case RUNLEVEL.READY:
						self.module.daemon.plugins['startup'].status = STATUS.WAITING_RUNNING
						self.module.daemon.remove_scheduled_signal('scheduler://startup/timeout:starting')
					case RUNLEVEL.RUNNING:
						self.module.daemon.plugins['startup'].status = STATUS.WAITING_WELCOME
						if self.module.daemon.plugins['frontend'].screen.split(':', 1).pop(0) != 'animations':
							self.module.daemon.queue_signal('startup', {'welcome': {}})
						else:
							animation = self.module.daemon.plugins['frontend'].screen.split(':', 1).pop(1)
							self.module.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop', \
							                                                                     'value': animation}}})
		return True


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin, key: str, old_screen: str, new_screen: str, phase: CommitPhase) -> bool:
		if new_screen in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_screen == 'idle':
					if self.module.daemon.plugins['brain'].runlevel == RUNLEVEL.READY:
						return False
			case CommitPhase.COMMIT:
				match new_screen:
					case 'none':
						if self.module.daemon.plugins['startup'].status == STATUS.WAITING_WELCOME:
							self.module.daemon.queue_signal('startup', {'welcome': {}})
					case other:
						if self.module.daemon.plugins['startup'].status == STATUS.WAITING_WELCOME:
							self.module.daemon.logger.warn(f"[startup] an unexpected screen '{new_screen}' is set, " \
							                               f"cancelling startup/welcome message")
							self.module.daemon.plugins['startup'].status = STATUS.FINISHED
		return True


	def startup_welcome(self) -> None:
		match self.module.daemon.plugins['brain'].status:
			case BRAIN_STATUS.AWAKE:
				self.module.daemon.logger.info(f"[startup] Now presenting welcome message")
				self.module.daemon.queue_signal('frontend', {'features': {'display': {'backlight': True}}})
				self.module.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
				self.module.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
				self.module.daemon.create_scheduled_signal(1.5, 'kalliope', {'command': {'name': 'welcome'}}, 'scheduler://kalliope/welcome:delay)')
			case BRAIN_STATUS.ASLEEP:
				self.module.daemon.logger.info(f"[startup] skipping welcome message (system is currently in sleep mode)")
				self.module.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
				self.module.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
				self.module.daemon.queue_signal('frontend', {'features': {'display': {'backlight': False}}})
				self.module.daemon.queue_signal('kalliope', {'status': 'sleeping'})
		self.module.daemon.plugins['startup'].status = STATUS.FINISHED

