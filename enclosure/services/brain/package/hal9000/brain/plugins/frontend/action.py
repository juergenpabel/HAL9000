from enum import StrEnum as enum_StrEnum
from json import loads as json_loads, \
                 dumps as json_dumps
from os.path import exists as os_path_exists
from datetime import datetime as datetime_datetime, \
                     timedelta as datetime_timedelta
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data, DataInvalid, RUNLEVEL, CommitPhase
from hal9000.brain.daemon import BRAIN_STATUS
from hal9000.brain.plugins.kalliope.action import Action as Kalliope_Action, \
                                                  KALLIOPE_STATUS


class FRONTEND_STATUS(enum_StrEnum):
	OFFLINE = 'offline'
	ONLINE  = 'online'


class Action(HAL9000_Action):

	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'frontend', action_name, plugin_status, **kwargs)
		self.daemon.plugins['frontend'].addRemoteNames(['screen', 'overlay'])
		self.daemon.plugins['frontend'].runlevel = DataInvalid.UNKNOWN, CommitPhase.COMMIT
		self.display_backlight = None


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['frontend-command-mqtt-prefix'] = configuration.get(section_name, 'frontend-command-mqtt-prefix', fallback='hal9000/command/frontend')
		self.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'frontend:screen',  self.runlevel_inhibitor_ready_screen)
		self.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'frontend:overlay', self.runlevel_inhibitor_ready_overlay)
		self.daemon.plugins['frontend'].addSignalHandler(self.on_frontend_signal)
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_runlevel_callback, 'runlevel')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_status_callback, 'status')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.mqtt_prefix = self.config['frontend-command-mqtt-prefix']


	def runlevel_inhibitor_ready_screen(self) -> bool:
		if self.daemon.plugins['frontend'].screen in [DataInvalid.UNINITIALIZED, DataInvalid.UNKNOWN]:
			return False
		if self.daemon.plugins['frontend'].getRemotePendingValue('screen') is not None:
			return False
		return True


	def runlevel_inhibitor_ready_overlay(self) -> bool:
		if self.daemon.plugins['frontend'].overlay in [DataInvalid.UNINITIALIZED, DataInvalid.UNKNOWN]:
			return False
		if self.daemon.plugins['frontend'].getRemotePendingValue('overlay') is not None:
			return False
		return True


	def on_frontend_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
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
						self.daemon.plugins['frontend'].status = DataInvalid.UNKNOWN, CommitPhase.COMMIT
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/status', 'payload': None})
					case RUNLEVEL.READY:
						if self.daemon.plugins['frontend'].status not in list(FRONTEND_STATUS):
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/status', 'payload': None})
					case RUNLEVEL.RUNNING:
						if self.daemon.plugins['frontend'].status not in list(FRONTEND_STATUS):
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/status', 'payload': None})
					case RUNLEVEL.KILLED:
						self.daemon.plugins['frontend'].status = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.daemon.plugins['frontend'].screen = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.daemon.plugins['frontend'].overlay = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.daemon.process_error('critical', '200', "System offline", f"Service 'frontend' unavailable")
		return True


	def on_frontend_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_status not in list(FRONTEND_STATUS):
					return False
			case CommitPhase.COMMIT:
				match new_status:
					case FRONTEND_STATUS.OFFLINE:
						self.daemon.plugins['frontend'].screen = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.daemon.plugins['frontend'].overlay = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					case FRONTEND_STATUS.ONLINE:
						self.daemon.plugins['frontend'].screen = DataInvalid.UNKNOWN, CommitPhase.COMMIT
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen', 'payload': None})
						self.daemon.plugins['frontend'].overlay = DataInvalid.UNKNOWN, CommitPhase.COMMIT
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/overlay', 'payload': None})
						datetime_now = datetime_datetime.now()
						epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
						synced = True if self.daemon.plugins['brain'].time == 'synchronized' else False
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/features',
						                                  'payload': {'time': {'epoch': epoch, 'synced': synced}}})
						if self.daemon.plugins['brain'].runlevel == RUNLEVEL.RUNNING:
							match self.daemon.plugins['brain'].status:
								case BRAIN_STATUS.AWAKE:
									if self.display_backlight != True:
										self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/features',
										                                  'payload': {'display': {'backlight': True}}})
										self.display_backlight = True
									self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
									self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
								case BRAIN_STATUS.ASLEEP:
									self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
									self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
									if self.display_backlight != False:
										self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/features',
										                                  'payload': {'display': {'backlight': False}}})
										self.display_backlight = False
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
				case RUNLEVEL.STARTING:
					if self.daemon.plugins['frontend'].runlevel == DataInvalid.UNKNOWN:
						self.daemon.plugins['frontend'].runlevel = RUNLEVEL.STARTING
				case RUNLEVEL.READY:
					if self.daemon.plugins['frontend'].runlevel == RUNLEVEL.STARTING:
						self.daemon.plugins['frontend'].runlevel = RUNLEVEL.READY
				case RUNLEVEL.RUNNING:
					self.daemon.plugins['frontend'].runlevel = RUNLEVEL.RUNNING
				case RUNLEVEL.KILLED:
					self.daemon.plugins['frontend'].runlevel = RUNLEVEL.KILLED, CommitPhase.COMMIT
					self.daemon.plugins['frontend'].status = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['frontend'].screen = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['frontend'].overlay = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
		if 'status' in signal:
			match signal['status']:
				case FRONTEND_STATUS.OFFLINE:
					self.daemon.plugins['frontend'].status = FRONTEND_STATUS.OFFLINE
				case FRONTEND_STATUS.ONLINE:
					self.daemon.plugins['frontend'].status = FRONTEND_STATUS.ONLINE
		if 'error' in signal:
			if self.daemon.plugins['frontend'].status == FRONTEND_STATUS.ONLINE:
				error = {'level': 'error', 'id': '000', 'title': 'UNEXPECTED ERROR', 'details': ''}
				for field in error.keys():
					if field in signal['error']:
						error[field] = signal['error'][field]
				self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'error', 'parameter': error}}})
		if 'environment' in signal:
			if self.daemon.plugins['frontend'].status == FRONTEND_STATUS.ONLINE:
				if 'set' in signal['environment']:
					if 'key' in signal['environment']['set'] and 'value' in signal['environment']['set']:
						key = signal['environment']['set']['key']
						value = signal['environment']['set']['value']
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/environment',
						                                  'payload': {'set': {'key': key, 'value': value}}})
		if 'settings' in signal:
			if self.daemon.plugins['frontend'].status == FRONTEND_STATUS.ONLINE:
				if 'set' in signal['settings']:
					if 'key' in signal['settings']['set'] and 'value' in signal['settings']['set']:
						key = signal['settings']['set']['key']
						value = signal['settings']['set']['value']
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/settings',
						                                  'payload': {'set': {'key': key, 'value': value}}})
		if 'features' in signal:
			if self.daemon.plugins['frontend'].status == FRONTEND_STATUS.ONLINE:
				self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/features',
				                                  'payload': signal['features']})
		if 'gui' in signal:
			if self.daemon.plugins['frontend'].status == FRONTEND_STATUS.ONLINE:
				if 'screen' in signal['gui']:
					screen_name = signal['gui']['screen']['name']
					screen_desc = signal['gui']['screen']['name']
					if 'parameter' in signal['gui']['screen'] and 'name' in signal['gui']['screen']['parameter']:
						screen_desc += ':' + signal['gui']['screen']['parameter']['name']
					elif 'parameter' in signal['gui']['screen'] and 'id' in signal['gui']['screen']['parameter']:
						screen_desc += ':' + signal['gui']['screen']['parameter']['id']
					if 'origin' in signal['gui']['screen'] and signal['gui']['screen']['origin'].startswith('frontend') == True:
						self.daemon.plugins['frontend'].screen = screen_name, CommitPhase.COMMIT
					else:
						self.daemon.plugins['frontend'].screen = screen_desc
						if self.daemon.plugins['frontend'].getRemotePendingValue('screen') == screen_desc:
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/screen',
							                                  'payload': {screen_name: signal['gui']['screen']['parameter']}})
				if 'overlay' in signal['gui']:
					overlay_name = signal['gui']['overlay']['name']
					overlay_desc = signal['gui']['overlay']['name']
					if 'parameter' in signal['gui']['overlay'] and 'name' in signal['gui']['overlay']['parameter']:
						overlay_desc += ':' + signal['gui']['overlay']['parameter']['name']
					elif 'parameter' in signal['gui']['overlay'] and 'id' in signal['gui']['overlay']['parameter']:
						overlay_desc += ':' + signal['gui']['overlay']['parameter']['id']
					if 'origin' in signal['gui']['overlay'] and signal['gui']['overlay']['origin'].startswith('frontend') == True:
						self.daemon.plugins['frontend'].overlay = overlay_name, CommitPhase.COMMIT
					else:
						self.daemon.plugins['frontend'].overlay = overlay_desc
						if self.daemon.plugins['frontend'].getRemotePendingValue('overlay') == overlay_desc:
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/gui/overlay',
							                                  'payload': {overlay_name: signal['gui']['overlay']['parameter']}})


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			match new_status:
				case BRAIN_STATUS.AWAKE:
					if self.daemon.plugins['brain'].runlevel in [RUNLEVEL.READY, RUNLEVEL.RUNNING]:
						if self.daemon.plugins['frontend'].status == FRONTEND_STATUS.ONLINE:
							if self.display_backlight != True:
								self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/features',
								                                  'payload': {'display': {'backlight': True}}})
								self.display_backlight = True
							if self.daemon.plugins['frontend'].screen != 'idle':
								if self.daemon.plugins['frontend'].getRemotePendingValue('screen') is None:
									self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
							if self.daemon.plugins['frontend'].overlay != 'none':
								if self.daemon.plugins['frontend'].getRemotePendingValue('overlay') is None:
									self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
				case BRAIN_STATUS.ASLEEP:
					if self.daemon.plugins['brain'].runlevel in [RUNLEVEL.READY, RUNLEVEL.RUNNING]:
						if self.daemon.plugins['frontend'].status == FRONTEND_STATUS.ONLINE:
							if self.daemon.plugins['frontend'].screen != 'none':
								if self.daemon.plugins['frontend'].getRemotePendingValue('screen') is None:
									self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
							if self.daemon.plugins['frontend'].overlay != 'none':
								if self.daemon.plugins['frontend'].getRemotePendingValue('overlay') is None:
									self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
							if self.display_backlight != False:
								self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/features',
								                                  'payload': {'display': {'backlight': False}}})
								self.display_backlight = False
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		if new_time in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			if self.daemon.plugins['frontend'].status == FRONTEND_STATUS.ONLINE:
				datetime_now = datetime_datetime.now()
				epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
				synced = True if new_time == 'synchronized' else False
				self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/system/features',
				                                  'payload': {'time': {'epoch': epoch, 'synced': synced}}})
		return True


	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			match new_runlevel:
				case RUNLEVEL.STARTING:
					if old_runlevel == RUNLEVEL.KILLED:
						match self.daemon.plugins['brain'].status:
							case BRAIN_STATUS.AWAKE:
								self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
								self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
							case BRAIN_STATUS.ASLEEP:
								self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
								self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			if self.daemon.plugins['frontend'].status == FRONTEND_STATUS.ONLINE:
				if old_status == KALLIOPE_STATUS.WAITING and new_status == KALLIOPE_STATUS.LISTENING:
					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
				if old_status == KALLIOPE_STATUS.SPEAKING and new_status == KALLIOPE_STATUS.WAITING:
					self.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop', 'value': 'false'}}})
		return True

