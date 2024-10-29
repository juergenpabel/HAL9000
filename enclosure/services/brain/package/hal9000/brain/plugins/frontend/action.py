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


class DISPLAY(enum_StrEnum):
	ON = 'on'
	OFF = 'off'


class Action(HAL9000_Action):

	def __init__(self, action_instance: str, **kwargs) -> None:
		super().__init__('frontend', **kwargs)
		self.addRemoteNames(['display', 'screen', 'overlay'])
		self.runlevel = DataInvalid.UNKNOWN, CommitPhase.COMMIT
		self.status = DataInvalid.UNKNOWN, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.config['frontend-command-mqtt-prefix'] = configuration.get(section_name, 'frontend-command-mqtt-prefix', fallback='hal9000/command/frontend')
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.SYNCING, 'frontend: frontend.status!=online',  self.runlevel_inhibitor_syncing_status)
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.SYNCING, 'frontend: frontend.display==unknown',  self.runlevel_inhibitor_syncing_display)
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.SYNCING, 'frontend: frontend.screen==unknown',  self.runlevel_inhibitor_syncing_screen)
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.SYNCING, 'frontend: frontend.overlay==unknown',  self.runlevel_inhibitor_syncing_overlay)
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.PREPARING, 'frontend: frontend.screen!=none',  self.runlevel_inhibitor_preparing_screen)
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.PREPARING, 'frontend: frontend.overlay!=none',  self.runlevel_inhibitor_preparing_overlay)
		self.module.daemon.plugins['frontend'].addSignalHandler(self.on_frontend_signal)
		self.module.daemon.plugins['frontend'].addNameCallback(self.on_frontend_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['frontend'].addNameCallback(self.on_frontend_status_callback, 'status')
		self.module.daemon.plugins['frontend'].addNameCallback(self.on_frontend_display_callback, 'display')
		self.module.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.module.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.module.mqtt_prefix = self.module.config['frontend-command-mqtt-prefix']


	async def runlevel_inhibitor_syncing_status(self) -> bool:
		if self.status != STATUS.ONLINE:
			return False
		return True


	async def runlevel_inhibitor_syncing_display(self) -> bool:
		if self.display in list(DataInvalid):
			return False
		return True


	async def runlevel_inhibitor_syncing_screen(self) -> bool:
		if self.screen in list(DataInvalid):
			return False
		return True


	async def runlevel_inhibitor_syncing_overlay(self) -> bool:
		if self.overlay in list(DataInvalid):
			return False
		return True


	async def runlevel_inhibitor_preparing_screen(self) -> bool:
		if self.screen != 'none':
			return False
		await self.signal({'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
		return True


	async def runlevel_inhibitor_preparing_overlay(self) -> bool:
		if self.overlay != 'none':
			return False
		return True


	async def on_frontend_signal(self, plugin: HAL9000_Plugin, signal: dict) -> None:
		if 'runlevel' in signal:
			match signal['runlevel']:
				case None | '':
					self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/runlevel', 'payload': None})
				case RUNLEVEL.KILLED:
					self.runlevel = RUNLEVEL.KILLED, CommitPhase.COMMIT
				case other:
					self.runlevel = signal['runlevel']
		if 'status' in signal:
			match signal['status']:
				case None | '':
					self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/status', 'payload': None})
				case other:
					self.status = signal['status']
		if 'system' in signal:
			if 'environment' in signal['system']:
				if self.status == STATUS.ONLINE:
					if 'set' in signal['system']['environment']:
						if 'key' in signal['system']['environment']['set'] and 'value' in signal['system']['environment']['set']:
							key = signal['system']['environment']['set']['key']
							value = signal['system']['environment']['set']['value']
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/environment', \
							                                         'payload': {'set': {'key': key, 'value': value}}})
			if 'settings' in signal['system']:
				if self.status == STATUS.ONLINE:
					if 'set' in signal['system']['settings']:
						if 'key' in signal['system']['settings']['set'] and 'value' in signal['system']['settings']['set']:
							key = signal['system']['settings']['set']['key']
							value = signal['system']['settings']['set']['value']
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/settings', \
							                                         'payload': {'set': {'key': key, 'value': value}}})
			if 'features' in signal['system']:
				if self.status == STATUS.ONLINE:
					commit_phase = CommitPhase.LOCAL_REQUESTED
					if 'origin' in signal and signal['origin'].startswith('frontend') == True:
						commit_phase = CommitPhase.COMMIT
					if 'display' in signal['system']['features'] and 'backlight' in signal['system']['features']['display']:
						match signal['system']['features']['display']['backlight']:
							case True:
								self.display = DISPLAY.ON, commit_phase
							case False:
								self.display = DISPLAY.OFF, commit_phase
					if 'time' in signal['system']['features'] and 'synced' in signal['system']['features']['time']:
						self.module.daemon.plugins['brain'].time = str(signal['system']['features']['time']['synced']).lower(), commit_phase
			if 'error' in signal['system']:
				if self.status == STATUS.ONLINE:
					error = {'level': 'error', 'id': '000', 'title': 'UNEXPECTED ERROR', 'details': ''}
					for field in error.keys():
						if field in signal['system']['error']:
							error[field] = signal['system']['error'][field]
					await self.module.daemon.plugins['frontend'].signal({'gui': {'screen': {'name': 'error', 'parameter': error}}})
		if 'gui' in signal:
			if self.status == STATUS.ONLINE:
				if 'screen' in signal['gui']:
					screen_name = signal['gui']['screen']['name']
					screen_desc = signal['gui']['screen']['name']
					if 'parameter' in signal['gui']['screen'] and 'name' in signal['gui']['screen']['parameter']:
						screen_desc += ':' + signal['gui']['screen']['parameter']['name']
					elif 'parameter' in signal['gui']['screen'] and 'id' in signal['gui']['screen']['parameter']:
						screen_desc += ':' + signal['gui']['screen']['parameter']['id']
					if 'origin' in signal and signal['origin'].startswith('frontend') == True:
						self.screen = screen_name, CommitPhase.COMMIT
					else:
						self.screen = screen_desc
						if self.getRemotePendingValue('screen') == screen_desc:
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/gui/screen', \
							                                         'payload': {screen_name: signal['gui']['screen']['parameter']}})
				if 'overlay' in signal['gui']:
					overlay_name = signal['gui']['overlay']['name']
					overlay_desc = signal['gui']['overlay']['name']
					if 'parameter' in signal['gui']['overlay'] and 'name' in signal['gui']['overlay']['parameter']:
						overlay_desc += ':' + signal['gui']['overlay']['parameter']['name']
					elif 'parameter' in signal['gui']['overlay'] and 'id' in signal['gui']['overlay']['parameter']:
						overlay_desc += ':' + signal['gui']['overlay']['parameter']['id']
					if 'origin' in signal and signal['origin'].startswith('frontend') == True:
						self.overlay = overlay_name, CommitPhase.COMMIT
					else:
						self.overlay = overlay_desc
						if self.getRemotePendingValue('overlay') == overlay_desc:
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/gui/overlay', \
							                                         'payload': {overlay_name: signal['gui']['overlay']['parameter']}})


	def on_frontend_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_runlevel not in list(RUNLEVEL):
					return False
			case CommitPhase.COMMIT:
				if old_runlevel == RUNLEVEL.KILLED:
					self.status = DataInvalid.UNKNOWN, CommitPhase.COMMIT
					self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/status', 'payload': None})
				if new_runlevel == RUNLEVEL.KILLED:
					self.status = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.display = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.screen = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.overlay = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
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
				if old_status == DataInvalid.UNKNOWN:
					self.display = DataInvalid.UNKNOWN, CommitPhase.COMMIT
					self.screen = DataInvalid.UNKNOWN, CommitPhase.COMMIT
					self.overlay = DataInvalid.UNKNOWN, CommitPhase.COMMIT
				match new_status:
					case STATUS.OFFLINE:
						self.display = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.screen = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
						self.overlay = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					case STATUS.ONLINE:
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', 'payload': None})
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/gui/screen', 'payload': None})
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/gui/overlay', 'payload': None})
						datetime_now = datetime_datetime.now()
						epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
						synced = True if self.module.daemon.plugins['brain'].time == 'synchronized' else False
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
						                                         'payload': {'time': {'epoch': epoch, 'synced': synced}}})
		return True


	def on_frontend_display_callback(self, plugin: HAL9000_Plugin, key: str, old_display: str, new_display: str, phase: CommitPhase) -> bool:
		if new_display in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_display not in list(DISPLAY):
					return False
			case CommitPhase.REMOTE_REQUESTED:
				self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
				                                         'payload': {'display': {'backlight': new_display == DISPLAY.ON}}})
		return True


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin, key: str, old_screen: str, new_screen: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			self.module.daemon.logger.debug(f"[frontend] STATUS at screen transition = {self.module.daemon}")
		return True


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			match new_runlevel:
				case RUNLEVEL.SYNCING:
					self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/status', 'payload': None})
				case RUNLEVEL.PREPARING:
					match self.module.daemon.plugins['frontend'].screen.split(':', 1).pop(0):
						case 'animations':
							animation = self.module.daemon.plugins['frontend'].screen.split(':', 1).pop(1)
							self.module.daemon.queue_signal('frontend', {'system': {'environment': {'set': {'key': 'gui/screen:animations/loop', \
							                                                                                'value': animation}}}})
						case other:
							self.module.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
							self.module.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
				case RUNLEVEL.RUNNING:
					match self.module.daemon.plugins['brain'].status:
						case BRAIN_STATUS.AWAKE:
							self.module.daemon.queue_signal('frontend', {'system': {'features': {'display': {'backlight': True}}}})
						case BRAIN_STATUS.ASLEEP:
							self.module.daemon.queue_signal('frontend', {'system': {'features': {'display': {'backlight': False}}}})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			match new_status:
				case BRAIN_STATUS.AWAKE:
					if self.status == STATUS.ONLINE:
						self.module.daemon.queue_signal('frontend', {'system': {'features': {'display': {'backlight': True}}}})
				case BRAIN_STATUS.ASLEEP:
					if self.status == STATUS.ONLINE:
						self.module.daemon.queue_signal('frontend', {'system': {'features': {'display': {'backlight': False}}}})
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		if new_time in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			if self.status == STATUS.ONLINE:
				datetime_now = datetime_datetime.now()
				epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
				synced = True if new_time == 'synchronized' else False
				self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/system/features', \
				                                         'payload': {'time': {'epoch': epoch, 'synced': synced}}})
		return True


	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT and old_runlevel == RUNLEVEL.KILLED:
			self.module.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
			self.module.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			if self.status == STATUS.ONLINE:
				if old_status == KALLIOPE_STATUS.WAITING and new_status == KALLIOPE_STATUS.LISTENING:
					self.module.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
				if old_status == KALLIOPE_STATUS.SPEAKING and new_status == KALLIOPE_STATUS.WAITING:
					self.module.daemon.queue_signal('frontend', {'system': {'environment': {'set': {'key': 'gui/screen:animations/loop', \
					                                                                                'value': 'hal9000'}}}})
		return True

