from json import loads as json_loads, \
                 dumps as json_dumps
from os.path import exists as os_path_exists
from datetime import datetime as datetime_datetime, \
                     timedelta as datetime_timedelta
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data, CommitPhase
from hal9000.brain.daemon import Brain
from hal9000.brain.plugins.kalliope.action import Action as Kalliope_Action


class Action(HAL9000_Action):

	FRONTEND_STATUS_OFFLINE  = 'offline'
	FRONTEND_STATUS_ONLINE   = 'online'

	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'frontend', action_name, plugin_status, **kwargs)
		self.daemon.plugins['frontend'].addRemoteNames(['screen', 'overlay'])
		self.daemon.plugins['frontend'].runlevel = HAL9000_Action.RUNLEVEL_UNKNOWN, CommitPhase.COMMIT
		self.display_power = None


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['frontend-command-mqtt-prefix'] = configuration.get(section_name, 'frontend-command-mqtt-prefix', fallback='hal9000/command/frontend')
		self.daemon.add_runlevel_inhibitor(HAL9000_Plugin.RUNLEVEL_READY, 'frontend:status',  self.runlevel_inhibitor_ready_status)
		self.daemon.add_runlevel_inhibitor(HAL9000_Plugin.RUNLEVEL_READY, 'frontend:screen',  self.runlevel_inhibitor_ready_screen)
		self.daemon.add_runlevel_inhibitor(HAL9000_Plugin.RUNLEVEL_READY, 'frontend:overlay', self.runlevel_inhibitor_ready_overlay)
		self.daemon.plugins['frontend'].addSignalHandler(self.on_frontend_signal)
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_runlevel_callback, 'runlevel')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_status_callback, 'status')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.mqtt_prefix = self.config['frontend-command-mqtt-prefix']


	def runlevel(self) -> str:
		return self.daemon.plugins['frontend'].runlevel


	def runlevel_error(self) -> dict:
		return {'id': '200',
		        'level': 'critical',
		        'title': "Service 'frontend' unavailable (arduino/flet backends)"}


	def runlevel_inhibitor_ready_status(self) -> bool:
		if self.daemon.plugins['frontend'].status not in [Action.FRONTEND_STATUS_OFFLINE, Action.FRONTEND_STATUS_ONLINE]:
			return False
		return True


	def runlevel_inhibitor_ready_screen(self) -> bool:
		if self.daemon.plugins['frontend'].screen == 'unknown':
			return False
		if self.daemon.plugins['frontend'].getRemotePendingValue('screen') is not None:
			return False
		return True


	def runlevel_inhibitor_ready_overlay(self) -> bool:
		if self.daemon.plugins['frontend'].overlay == 'unknown':
			return False
		if self.daemon.plugins['frontend'].getRemotePendingValue('overlay') is not None:
			return False
		return True


	def on_frontend_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				match old_runlevel:
					case HAL9000_Plugin.RUNLEVEL_UNKNOWN:
						if new_runlevel not in [HAL9000_Plugin.RUNLEVEL_STARTING, HAL9000_Plugin.RUNLEVEL_READY, HAL9000_Plugin.RUNLEVEL_RUNNING]:
							return False
					case HAL9000_Plugin.RUNLEVEL_STARTING:
						if new_runlevel != HAL9000_Plugin.RUNLEVEL_READY:
							return False
					case HAL9000_Plugin.RUNLEVEL_READY:
						if new_runlevel != HAL9000_Plugin.RUNLEVEL_RUNNING:
							return False
			case CommitPhase.COMMIT:
				match new_runlevel:
					case HAL9000_Plugin.RUNLEVEL_STARTING:
						self.daemon.plugins['frontend'].status = 'unknown', CommitPhase.COMMIT
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/status', 'payload': None})
					case HAL9000_Plugin.RUNLEVEL_READY:
						if self.daemon.plugins['frontend'].status not in [Action.FRONTEND_STATUS_OFFLINE, Action.FRONTEND_STATUS_ONLINE]:
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/status', 'payload': None})
					case HAL9000_Plugin.RUNLEVEL_RUNNING:
						if self.daemon.plugins['frontend'].status not in [Action.FRONTEND_STATUS_OFFLINE, Action.FRONTEND_STATUS_ONLINE]:
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/status', 'payload': None})
					case HAL9000_Plugin.RUNLEVEL_KILLED:
						self.daemon.plugins['frontend'].status = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
						self.daemon.plugins['frontend'].screen = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
						self.daemon.plugins['frontend'].overlay = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
						self.daemon.process_error('critical', '200', "System offline", f"Service 'frontend' unavailable")
		return True


	def on_frontend_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_status not in [HAL9000_Plugin_Data.STATUS_UNINITIALIZED, Action.FRONTEND_STATUS_OFFLINE, Action.FRONTEND_STATUS_ONLINE]:
					return False
			case CommitPhase.COMMIT:
				match new_status:
					case Action.FRONTEND_STATUS_OFFLINE:
						self.daemon.plugins['frontend'].screen = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
						self.daemon.plugins['frontend'].overlay = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
					case Action.FRONTEND_STATUS_ONLINE:
						self.daemon.plugins['frontend'].screen = 'unknown', CommitPhase.COMMIT
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen', 'payload': None})
						self.daemon.plugins['frontend'].overlay = 'unknown', CommitPhase.COMMIT
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/overlay', 'payload': None})
						datetime_now = datetime_datetime.now()
						epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
						synced = True if self.daemon.plugins['brain'].time == 'synchronized' else False
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/features',
						                                  'payload': {'time': {'epoch': epoch, 'synced': synced}}})
						if self.daemon.plugins['brain'].runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING:
							match self.daemon.plugins['brain'].status:
								case Brain.STATUS_AWAKE:
									if self.display_power is not True:
										self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen',
										                                  'payload': {'on': {}}})
										self.display_power = True
									self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
									self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
								case Brain.STATUS_ASLEEP:
									self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
									self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
									if self.display_power is not False:
										self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen',
										                                  'payload': {'off': {}}})
										self.display_power = False
		return True


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_screen: str, new_screen: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			self.daemon.logger.debug(f"[frontend] STATUS at screen transition = { {k: v for k,v in self.daemon.plugins.items() if v.hidden is False} }")
		return True


	async def on_frontend_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'runlevel' in signal:
			match signal['runlevel']:
				case '':
					self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/runlevel', 'payload': None})
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					if self.daemon.plugins['frontend'].runlevel == HAL9000_Plugin.RUNLEVEL_UNKNOWN:
						self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_STARTING
				case HAL9000_Plugin.RUNLEVEL_READY:
					if self.daemon.plugins['frontend'].runlevel == HAL9000_Plugin.RUNLEVEL_STARTING:
						self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_READY
				case HAL9000_Plugin.RUNLEVEL_RUNNING:
					self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_RUNNING
				case HAL9000_Plugin.RUNLEVEL_KILLED:
					self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_KILLED, CommitPhase.COMMIT
					self.daemon.plugins['frontend'].status = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['frontend'].screen = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['frontend'].overlay = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
		if 'status' in signal:
			match signal['status']:
				case Action.FRONTEND_STATUS_OFFLINE:
					self.daemon.plugins['frontend'].status = Action.FRONTEND_STATUS_OFFLINE
				case Action.FRONTEND_STATUS_ONLINE:
					self.daemon.plugins['frontend'].status = Action.FRONTEND_STATUS_ONLINE
		if 'error' in signal:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				error = {'level': 'error', 'id': '000', 'title': 'UNEXPECTED ERROR', 'details': ''}
				for field in error.keys():
					if field in signal['error']:
						error[field] = signal['error'][field]
				self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'error', 'parameter': error}}})
		if 'environment' in signal:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				if 'set' in signal['environment']:
					if 'key' in signal['environment']['set'] and 'value' in signal['environment']['set']:
						key = signal['environment']['set']['key']
						value = signal['environment']['set']['value']
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/environment',
						                                  'payload': {'set': {'key': key, 'value': value}}})
		if 'settings' in signal:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				if 'set' in signal['settings']:
					if 'key' in signal['settings']['set'] and 'value' in signal['settings']['set']:
						key = signal['settings']['set']['key']
						value = signal['settings']['set']['value']
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/settings',
						                                  'payload': {'set': {'key': key, 'value': value}}})
		if 'gui' in signal:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				if 'screen' in signal['gui']:
					screen = signal['gui']['screen']['name']
					if 'parameter' in signal['gui']['screen'] and 'name' in signal['gui']['screen']['parameter']:
						screen += ':' + signal['gui']['screen']['parameter']['name']
					elif 'parameter' in signal['gui']['screen'] and 'id' in signal['gui']['screen']['parameter']:
						screen += ':' + signal['gui']['screen']['parameter']['id']
					if 'origin' in signal['gui']['screen'] and signal['gui']['screen']['origin'].startswith('frontend') == True:
						self.daemon.plugins['frontend'].screen = screen, CommitPhase.COMMIT
					else:
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen',
						                                  'payload': {signal['gui']['screen']['name']: signal['gui']['screen']['parameter']}})
						self.daemon.plugins['frontend'].screen = screen
				if 'overlay' in signal['gui']:
					overlay = signal['gui']['overlay']['name']
					if 'parameter' in signal['gui']['overlay'] and 'name' in signal['gui']['overlay']['parameter']:
						overlay += ':' + signal['gui']['overlay']['parameter']['name']
					elif 'parameter' in signal['gui']['overlay'] and 'id' in signal['gui']['overlay']['parameter']:
						overlay += ':' + signal['gui']['overlay']['parameter']['id']
					if 'origin' in signal['gui']['overlay'] and signal['gui']['overlay']['origin'].startswith('frontend') == True:
						self.daemon.plugins['frontend'].overlay = overlay, CommitPhase.COMMIT
					else:
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/overlay',
						                                  'payload': {signal['gui']['overlay']['name']: signal['gui']['overlay']['parameter']}})
						self.daemon.plugins['frontend'].overlay = overlay


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			if old_runlevel == HAL9000_Plugin.RUNLEVEL_STARTING and new_runlevel == HAL9000_Plugin.RUNLEVEL_READY:
				if self.display_power is not True:
					self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen', 'payload': {'on': {}}})
					self.display_power = True
				if self.daemon.plugins['frontend'].screen != 'idle':
					if self.daemon.plugins['frontend'].getRemotePendingValue('screen') is None:
						self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
				if self.daemon.plugins['frontend'].overlay != 'none':
					if self.daemon.plugins['frontend'].getRemotePendingValue('overlay') is None:
						self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			match new_status:
				case Brain.STATUS_AWAKE:
					if old_status == Brain.STATUS_ASLEEP and self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
						if self.display_power is not True:
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen', 'payload': {'on': {}}})
							self.display_power = True
						if self.daemon.plugins['frontend'].screen != 'idle':
							if self.daemon.plugins['frontend'].getRemotePendingValue('screen') is None:
								self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
						if self.daemon.plugins['frontend'].overlay != 'none':
							if self.daemon.plugins['frontend'].getRemotePendingValue('overlay') is None:
								self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
				case Brain.STATUS_ASLEEP:
					if old_status == Brain.STATUS_AWAKE and self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
						if self.daemon.plugins['frontend'].screen != 'none':
							if self.daemon.plugins['frontend'].getRemotePendingValue('screen') is None:
								self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
						if self.daemon.plugins['frontend'].overlay != 'none':
							if self.daemon.plugins['frontend'].getRemotePendingValue('overlay') is None:
								self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
						if self.display_power is not False:
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen', 'payload': {'off': {}}})
							self.display_power = False
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				datetime_now = datetime_datetime.now()
				epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
				synced = True if new_time == 'synchronized' else False
				self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/features',
				                                  'payload': {'time': {'epoch': epoch, 'synced': synced}}})
		return True


	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			match new_runlevel:
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					if old_runlevel == HAL9000_Plugin.RUNLEVEL_KILLED:
						match self.daemon.plugins['brain'].status:
							case Brain.STATUS_AWAKE:
								self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
								self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
							case Brain.STATUS_ASLEEP:
								self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
								self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				if old_status == Kalliope_Action.KALLIOPE_STATUS_WAITING and new_status == Kalliope_Action.KALLIOPE_STATUS_LISTENING:
					self.daemon.plugins['frontend'].screen = 'animations:hal9000'
					self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen',
					                                  'payload': {'animations': {'name': 'hal9000'}}})
				if old_status == Kalliope_Action.KALLIOPE_STATUS_SPEAKING and new_status == Kalliope_Action.KALLIOPE_STATUS_WAITING:
					self.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop', 'value': 'false'}}})
		return True

