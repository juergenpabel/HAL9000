from enum import StrEnum as enum_StrEnum
from json import loads as json_loads, \
                 dumps as json_dumps
from os.path import exists as os_path_exists
from datetime import datetime as datetime_datetime, \
                     timedelta as datetime_timedelta
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, DataInvalid, RUNLEVEL, CommitPhase
from hal9000.brain.plugins.brain.action import STATUS as BRAIN_STATUS
from hal9000.brain.plugins.kalliope.action import STATUS as KALLIOPE_STATUS


class STATUS(enum_StrEnum):
	OFFLINE = 'offline'
	ONLINE  = 'online'


class Action(HAL9000_Action):

	def __init__(self, action_instance: str, **kwargs) -> None:
		super().__init__('frontend', **kwargs)
		self.module.daemon.plugins['frontend'].addRemoteNames(['screen', 'overlay'])
		self.module.daemon.plugins['frontend'].runlevel = DataInvalid.UNKNOWN, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.config['frontend-command-mqtt-prefix'] = configuration.get(section_name, 'frontend-command-mqtt-prefix', fallback='hal9000/command/frontend')
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'frontend:screen',  self.runlevel_inhibitor_ready_screen)
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'frontend:overlay', self.runlevel_inhibitor_ready_overlay)
		self.module.daemon.plugins['frontend'].addSignalHandler(self.on_frontend_signal)
		self.module.daemon.plugins['frontend'].addNameCallback(self.on_frontend_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['frontend'].addNameCallback(self.on_frontend_status_callback, 'status')
		self.module.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.module.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.module.mqtt_prefix = self.module.config['frontend-command-mqtt-prefix']


	def runlevel_inhibitor_ready_screen(self) -> bool:
		if self.module.daemon.plugins['frontend'].screen in [DataInvalid.UNINITIALIZED, DataInvalid.UNKNOWN]:
			return False
		if self.module.daemon.plugins['frontend'].getRemotePendingValue('screen') is not None:
			return False
		return True


	def runlevel_inhibitor_ready_overlay(self) -> bool:
		if self.module.daemon.plugins['frontend'].overlay in [DataInvalid.UNINITIALIZED, DataInvalid.UNKNOWN]:
			return False
		if self.module.daemon.plugins['frontend'].getRemotePendingValue('overlay') is not None:
			return False
		return True


	def on_frontend_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				match old_runlevel:
					case DataInvalid.UNKNOWN:
						if new_runlevel not in list(RUNLEVEL):
							return False
					case RUNLEVEL.STARTING:
						if new_runlevel != RUNLEVEL.READY:
							return False
					case RUNLEVEL.READY:
						if new_runlevel != RUNLEVEL.RUNNING:
							return False
			case CommitPhase.COMMIT:
				match new_runlevel:
					case RUNLEVEL.STARTING:
						self.module.daemon.plugins['frontend'].status = DataInvalid.UNKNOWN, CommitPhase.COMMIT
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/status', 'payload': None})
					case RUNLEVEL.READY:
						if self.module.daemon.plugins['frontend'].status not in list(STATUS):
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/status', 'payload': None})
					case RUNLEVEL.RUNNING:
						if self.module.daemon.plugins['frontend'].status not in list(STATUS):
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/status', 'payload': None})
					case RUNLEVEL.KILLED:
						self.module.daemon.plugins['frontend'].status = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.module.daemon.plugins['frontend'].screen = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.module.daemon.plugins['frontend'].overlay = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.module.daemon.process_error('critical', '200', "System offline", f"Service 'frontend' unavailable")
		return True


	def on_frontend_status_callback(self, plugin: HAL9000_Plugin, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_status not in list(STATUS):
					return False
			case CommitPhase.COMMIT:
				match new_status:
					case STATUS.OFFLINE:
						self.module.daemon.plugins['frontend'].screen = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.module.daemon.plugins['frontend'].overlay = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					case STATUS.ONLINE:
						self.module.daemon.plugins['frontend'].screen = DataInvalid.UNKNOWN, CommitPhase.COMMIT
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/gui/screen', 'payload': None})
						self.module.daemon.plugins['frontend'].overlay = DataInvalid.UNKNOWN, CommitPhase.COMMIT
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/gui/overlay', 'payload': None})
						datetime_now = datetime_datetime.now()
						epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
						synced = True if self.module.daemon.plugins['brain'].time == 'synchronized' else False
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
						                                         'payload': {'time': {'epoch': epoch, 'synced': synced}}})
						if self.module.daemon.plugins['brain'].runlevel == RUNLEVEL.RUNNING:
							self.module.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
							self.module.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
							match self.module.daemon.plugins['brain'].status:
								case BRAIN_STATUS.AWAKE:
									self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
									                                         'payload': {'display': {'backlight': True}}})
								case BRAIN_STATUS.ASLEEP:
									self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
									                                         'payload': {'display': {'backlight': False}}})
		return True


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin, key: str, old_screen: str, new_screen: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			self.module.daemon.logger.debug(f"[frontend] STATUS at screen transition = {self.module.daemon}")
		return True


	async def on_frontend_signal(self, plugin: HAL9000_Plugin, signal: dict) -> None:
		if 'runlevel' in signal:
			match signal['runlevel']:
				case '':
					self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/runlevel', 'payload': None})
				case RUNLEVEL.STARTING:
					if self.module.daemon.plugins['frontend'].runlevel == DataInvalid.UNKNOWN:
						self.module.daemon.plugins['frontend'].runlevel = RUNLEVEL.STARTING
				case RUNLEVEL.READY:
					if self.module.daemon.plugins['frontend'].runlevel == RUNLEVEL.STARTING:
						self.module.daemon.plugins['frontend'].runlevel = RUNLEVEL.READY
				case RUNLEVEL.RUNNING:
					self.module.daemon.plugins['frontend'].runlevel = RUNLEVEL.RUNNING
				case RUNLEVEL.KILLED:
					self.module.daemon.plugins['frontend'].runlevel = RUNLEVEL.KILLED, CommitPhase.COMMIT
					self.module.daemon.plugins['frontend'].status = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.module.daemon.plugins['frontend'].screen = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.module.daemon.plugins['frontend'].overlay = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
		if 'status' in signal:
			match signal['status']:
				case STATUS.OFFLINE:
					self.module.daemon.plugins['frontend'].status = STATUS.OFFLINE
				case STATUS.ONLINE:
					self.module.daemon.plugins['frontend'].status = STATUS.ONLINE
		if 'error' in signal:
			if self.module.daemon.plugins['frontend'].status == STATUS.ONLINE:
				error = {'level': 'error', 'id': '000', 'title': 'UNEXPECTED ERROR', 'details': ''}
				for field in error.keys():
					if field in signal['error']:
						error[field] = signal['error'][field]
				self.module.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'error', 'parameter': error}}})
		if 'environment' in signal:
			if self.module.daemon.plugins['frontend'].status == STATUS.ONLINE:
				if 'set' in signal['environment']:
					if 'key' in signal['environment']['set'] and 'value' in signal['environment']['set']:
						key = signal['environment']['set']['key']
						value = signal['environment']['set']['value']
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/environment', \
						                                         'payload': {'set': {'key': key, 'value': value}}})
		if 'settings' in signal:
			if self.module.daemon.plugins['frontend'].status == STATUS.ONLINE:
				if 'set' in signal['settings']:
					if 'key' in signal['settings']['set'] and 'value' in signal['settings']['set']:
						key = signal['settings']['set']['key']
						value = signal['settings']['set']['value']
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/settings', \
						                                         'payload': {'set': {'key': key, 'value': value}}})
		if 'features' in signal:
			if self.module.daemon.plugins['frontend'].status == STATUS.ONLINE:
				self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
				                                         'payload': signal['features']})
		if 'gui' in signal:
			if self.module.daemon.plugins['frontend'].status == STATUS.ONLINE:
				if 'screen' in signal['gui']:
					screen_name = signal['gui']['screen']['name']
					screen_desc = signal['gui']['screen']['name']
					if 'parameter' in signal['gui']['screen'] and 'name' in signal['gui']['screen']['parameter']:
						screen_desc += ':' + signal['gui']['screen']['parameter']['name']
					elif 'parameter' in signal['gui']['screen'] and 'id' in signal['gui']['screen']['parameter']:
						screen_desc += ':' + signal['gui']['screen']['parameter']['id']
					if 'origin' in signal['gui']['screen'] and signal['gui']['screen']['origin'].startswith('frontend') == True:
						self.module.daemon.plugins['frontend'].screen = screen_name, CommitPhase.COMMIT
					else:
						self.module.daemon.plugins['frontend'].screen = screen_desc
						if self.module.daemon.plugins['frontend'].getRemotePendingValue('screen') == screen_desc:
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/gui/screen', \
							                                         'payload': {screen_name: signal['gui']['screen']['parameter']}})
				if 'overlay' in signal['gui']:
					overlay_name = signal['gui']['overlay']['name']
					overlay_desc = signal['gui']['overlay']['name']
					if 'parameter' in signal['gui']['overlay'] and 'name' in signal['gui']['overlay']['parameter']:
						overlay_desc += ':' + signal['gui']['overlay']['parameter']['name']
					elif 'parameter' in signal['gui']['overlay'] and 'id' in signal['gui']['overlay']['parameter']:
						overlay_desc += ':' + signal['gui']['overlay']['parameter']['id']
					if 'origin' in signal['gui']['overlay'] and signal['gui']['overlay']['origin'].startswith('frontend') == True:
						self.module.daemon.plugins['frontend'].overlay = overlay_name, CommitPhase.COMMIT
					else:
						self.module.daemon.plugins['frontend'].overlay = overlay_desc
						if self.module.daemon.plugins['frontend'].getRemotePendingValue('overlay') == overlay_desc:
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/gui/overlay', \
							                                         'payload': {overlay_name: signal['gui']['overlay']['parameter']}})


	def on_brain_status_callback(self, plugin: HAL9000_Plugin, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			match new_status:
				case BRAIN_STATUS.AWAKE:
					if self.module.daemon.plugins['brain'].runlevel in [RUNLEVEL.READY, RUNLEVEL.RUNNING]:
						if self.module.daemon.plugins['frontend'].status == STATUS.ONLINE:
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
							                                         'payload': {'display': {'backlight': True}}})
				case BRAIN_STATUS.ASLEEP:
					if self.module.daemon.plugins['brain'].runlevel in [RUNLEVEL.READY, RUNLEVEL.RUNNING]:
						if self.module.daemon.plugins['frontend'].status == STATUS.ONLINE:
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
							                                         'payload': {'display': {'backlight': False}}})
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		if new_time in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			if self.module.daemon.plugins['frontend'].status == STATUS.ONLINE:
				datetime_now = datetime_datetime.now()
				epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
				synced = True if new_time == 'synchronized' else False
				self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
				                                         'payload': {'time': {'epoch': epoch, 'synced': synced}}})
		return True


	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			match new_runlevel:
				case RUNLEVEL.STARTING:
					if old_runlevel == RUNLEVEL.KILLED:
						self.module.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
						self.module.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			if self.module.daemon.plugins['frontend'].status == STATUS.ONLINE:
				if old_status == KALLIOPE_STATUS.WAITING and new_status == KALLIOPE_STATUS.LISTENING:
					self.module.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
				if old_status == KALLIOPE_STATUS.SPEAKING and new_status == KALLIOPE_STATUS.WAITING:
					self.module.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop', 'value': 'hal9000'}}})
		return True

