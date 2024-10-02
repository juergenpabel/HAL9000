from json import loads as json_loads, \
                 dumps as json_dumps
from os.path import exists as os_path_exists
from datetime import datetime as datetime_datetime, \
                     timedelta as datetime_timedelta
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data
from hal9000.brain.daemon import Daemon
from hal9000.brain.plugins.kalliope.action import Action as Kalliope_Action


class Action(HAL9000_Action):

	FRONTEND_STATUS_OFFLINE  = 'offline'
	FRONTEND_STATUS_ONLINE   = 'online'


	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'frontend', action_name, plugin_status, **kwargs)
		self.daemon.plugins['frontend'].addRemoteNames(['screen', 'overlay'])
		self.daemon.plugins['frontend'].runlevel = HAL9000_Action.RUNLEVEL_UNKNOWN


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['frontend-runlevel-mqtt-topic'] = configuration.get(section_name, 'frontend-runlevel-mqtt-topic', fallback='hal9000/command/frontend/runlevel')
		self.daemon.plugins['frontend'].addSignalHandler(self.on_frontend_signal)
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_runlevel_callback, 'runlevel')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_status_callback, 'status')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.daemon.plugins['brain'].addSignalHandler(self.on_brain_signal)


	def runlevel(self) -> str:
		return self.daemon.plugins['frontend'].runlevel


	def runlevel_error(self) -> dict:
		return {'id': '200',
		        'level': 'critical',
		        'title': "Service 'frontend' unavailable (arduino/flet backends)"}


	def send_frontend_command(self, topic: str, body: dict) -> None:
		self.daemon.mqtt_publish_queue.put_nowait({'topic': f'hal9000/command/frontend/{topic}', 'payload': json_dumps(body) if body is not None else None})


	def on_frontend_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, pending: bool) -> bool:
		if pending is False:
			match old_runlevel:
				case HAL9000_Plugin.RUNLEVEL_UNKNOWN:
					if new_runlevel not in [HAL9000_Plugin.RUNLEVEL_STARTING, \
					                        HAL9000_Plugin.RUNLEVEL_READY, \
					                        HAL9000_Plugin.RUNLEVEL_RUNNING]:
						return False
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					if new_runlevel != HAL9000_Plugin.RUNLEVEL_READY:
						return False
				case HAL9000_Plugin.RUNLEVEL_READY:
					if new_runlevel != HAL9000_Plugin.RUNLEVEL_RUNNING:
						return False
			match new_runlevel:
				case HAL9000_Plugin.RUNLEVEL_READY | HAL9000_Plugin.RUNLEVEL_RUNNING:
					if self.daemon.plugins['frontend'].status == HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
						self.send_frontend_command('status', None)
				case HAL9000_Plugin.RUNLEVEL_KILLED:
					self.daemon.process_error('critical', '200', "System offline", f"Service 'frontend' unavailable")
		return True


	def on_frontend_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, pending: bool) -> bool:
		if new_status not in [HAL9000_Plugin_Data.STATUS_UNINITIALIZED, Action.FRONTEND_STATUS_OFFLINE, Action.FRONTEND_STATUS_ONLINE]:
			return False
		if pending is False:
			match new_status:
				case Action.FRONTEND_STATUS_OFFLINE:
					self.daemon.plugins['frontend'].screen = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, HAL9000_Plugin_Data.STATUS_CONFIRMED
					self.daemon.plugins['frontend'].overlay = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, HAL9000_Plugin_Data.STATUS_CONFIRMED
				case Action.FRONTEND_STATUS_ONLINE:
					if self.daemon.plugins['brain'].runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING:
						datetime_now = datetime_datetime.now()
						epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
						synced = 'true' if self.daemon.plugins['brain'].time == 'synchronized' else 'false'
						self.send_frontend_command('system/features', {'time': {'epoch': epoch, 'synced': synced}})
						if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'on', 'parameter': {}}}})
						else:
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'off', 'parameter': {}}}})
					else:
						self.daemon.plugins['frontend'].screen = 'unknown', HAL9000_Plugin_Data.STATUS_CONFIRMED
						self.daemon.plugins['frontend'].overlay = 'unknown', HAL9000_Plugin_Data.STATUS_CONFIRMED
		return True


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_screen: str, new_screen: str, pending: bool) -> bool:
		if pending is False:
			self.daemon.logger.debug(f"STATUS at screen transition = {self.daemon.plugins}")
			if new_screen == 'on':
				self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
				self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	async def on_frontend_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'runlevel' in signal:
			match signal['runlevel']:
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					if self.daemon.plugins['frontend'].runlevel == HAL9000_Plugin.RUNLEVEL_UNKNOWN:
						self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_STARTING
				case HAL9000_Plugin.RUNLEVEL_READY:
					self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_READY
				case HAL9000_Plugin.RUNLEVEL_RUNNING:
					self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_RUNNING
				case HAL9000_Plugin.RUNLEVEL_KILLED:
					self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_KILLED
					self.daemon.plugins['frontend'].status = HAL9000_Plugin_Data.STATUS_UNINITIALIZED
					self.daemon.plugins['frontend'].screen = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, HAL9000_Plugin_Data.STATUS_CONFIRMED
					self.daemon.plugins['frontend'].overlay = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, HAL9000_Plugin_Data.STATUS_CONFIRMED
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
						self.send_frontend_command('system/environment', {'set': {'key': key, 'value': value}})
		if 'settings' in signal:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				if 'set' in signal['settings']:
					if 'key' in signal['settings']['set'] and 'value' in signal['settings']['set']:
						key = signal['settings']['set']['key']
						value = signal['settings']['set']['value']
						self.send_frontend_command('system/settings', {'set': {'key': key, 'value': value}})
		if 'gui' in signal:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				if 'screen' in signal['gui']:
					screen = signal['gui']['screen']['name']
					if 'parameter' in signal['gui']['screen'] and 'name' in signal['gui']['screen']['parameter']:
						screen += ':' + signal['gui']['screen']['parameter']['name']
					elif 'parameter' in signal['gui']['screen'] and 'id' in signal['gui']['screen']['parameter']:
						screen += ':' + signal['gui']['screen']['parameter']['id']
					status = None
					if 'origin' in signal['gui']['screen'] and signal['gui']['screen']['origin'].startswith('frontend') == True:
						status = HAL9000_Plugin_Data.STATUS_CONFIRMED
					else:
						self.send_frontend_command('gui/screen', {signal['gui']['screen']['name']: signal['gui']['screen']['parameter']})
						status = HAL9000_Plugin_Data.STATUS_REQUESTED
					self.daemon.plugins['frontend'].screen = screen, status
				if 'overlay' in signal['gui']:
					status = None
					if 'origin' in signal['gui']['overlay'] and signal['gui']['overlay']['origin'].startswith('frontend') == True:
						status = HAL9000_Plugin_Data.STATUS_CONFIRMED
					else:
						self.send_frontend_command('gui/overlay', {signal['gui']['overlay']['name']: signal['gui']['overlay']['parameter']})
						status = HAL9000_Plugin_Data.STATUS_REQUESTED
					self.daemon.plugins['frontend'].overlay = signal['gui']['overlay']['name'], status


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, pending: bool) -> bool:
		if pending is False:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				match new_status:
					case Daemon.BRAIN_STATUS_AWAKE:
						if old_status == Daemon.BRAIN_STATUS_ASLEEP:
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'on', 'parameter': {}}}})
							self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
					case Daemon.BRAIN_STATUS_ASLEEP:
						if old_status == Daemon.BRAIN_STATUS_AWAKE:
							self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'off', 'parameter': {}}}})
							self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_time: str, new_time: str, pending: bool) -> bool:
		if pending is False:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				datetime_now = datetime_datetime.now()
				epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
				synced = 'true' if new_time == 'synchronized' else 'false'
				self.send_frontend_command('system/features', {'time': {'epoch': epoch, 'synced': synced}})
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'runlevel' in signal:
			if signal['runlevel'] in [None, False, '', {}]:
				self.daemon.mqtt_publish_queue.put_nowait({'topic': self.config['frontend-runlevel-mqtt-topic'], 'payload': ''})


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, pending: bool) -> bool:
		if pending is False:
			if self.daemon.plugins['frontend'].status == Action.FRONTEND_STATUS_ONLINE:
				if old_status == Kalliope_Action.KALLIOPE_STATUS_WAITING and new_status == Kalliope_Action.KALLIOPE_STATUS_LISTENING:
					self.daemon.plugins['frontend'].screen = 'animations:hal9000'
					self.send_frontend_command('gui/screen', {'animations': {'name': 'hal9000'}})
				if old_status == Kalliope_Action.KALLIOPE_STATUS_SPEAKING and new_status == Kalliope_Action.KALLIOPE_STATUS_WAITING:
					self.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop', 'value': 'false'}}})
		return True

