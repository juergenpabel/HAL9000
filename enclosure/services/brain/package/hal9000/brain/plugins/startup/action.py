from json import dumps as json_dumps
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data


class Action(HAL9000_Action):
	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'startup', action_name, plugin_status, **kwargs)
		self.welcome_pending = False


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
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


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, pending: bool) -> bool:
		if pending is False:
			if new_runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING:
				match self.daemon.plugins['frontend'].screen:
					case 'animations:system-starting':
						self.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop', 'value': 'false'}}})
						self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
					case other:
						self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
						self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
				self.welcome_pending = True
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, pending: bool) -> bool:
		if pending is False:
			pass
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_time: str, new_time: str, pending: bool) -> bool:
		if pending is False:
			pass
		return True


	def on_frontend_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, pending: bool) -> bool:
		if pending is False:
			pass
		return True


	def on_frontend_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, pending: bool) -> bool:
		if pending is False:
			pass
		return True


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_screen: str, new_screen: str, pending: bool) -> bool:
		if pending is False:
			if self.welcome_pending is True:
				if new_screen == 'none':
					match self.daemon.plugins['brain'].status:
						case Daemon.BRAIN_STATUS_ASLEEP:
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'off', 'parameter': {}}}})
							self.daemon.queue_signal('kalliope', {'status': 'sleeping'})
						case Daemon.BRAIN_STATUS_AWAKE:
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations',
							                                                         'parameter': {'name': 'hal9000'}}}})
							self.daemon.schedule_signal(1.5, 'kalliope', {'command': {'name': 'welcome', 'parameter': None}},
							                            'scheduler://kalliope/welcome:delay)')
					self.welcome_pending = False
		return True

 
	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, pending: bool) -> bool:
		if pending is False:
			pass
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, pending: bool) -> bool:
		if pending is False:
			pass
		return True


