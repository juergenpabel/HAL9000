from json import dumps as json_dumps
from os.path import exists as os_path_exists
from datetime import datetime as datetime_datetime, \
                     timedelta as datetime_timedelta
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Status
from hal9000.brain.daemon import Daemon
from hal9000.brain.plugins.kalliope.action import Action as Kalliope_Action


class Action(HAL9000_Action):

	FRONTEND_STATUS_OFFLINE  = 'offline'
	FRONTEND_STATUS_ONLINE   = 'online'


	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Status, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'frontend', action_name, plugin_status, **kwargs)
		self.daemon.plugins['frontend'].addNames(['screen', 'overlay'])
		self.daemon.plugins['frontend'].runlevel = HAL9000_Action.RUNLEVEL_UNKNOWN


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['frontend-runlevel-mqtt-topic'] = configuration.get(section_name, 'frontend-runlevel-mqtt-topic', fallback='hal9000/command/frontend/runlevel')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_runlevel_callback, 'runlevel')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.plugins['frontend'].addSignalHandler(self.on_frontend_signal)
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.daemon.plugins['brain'].addSignalHandler(self.on_brain_signal)


	def runlevel(self) -> str:
		return self.daemon.plugins['frontend'].runlevel


	def runlevel_error(self) -> dict:
		return {'id': '01',
		        'level': 'error',
		        'message': "No connection to microcontroller."}


	def send_frontend_command(self, topic:str , body: dict) -> None:
		self.daemon.mqtt_publish_queue.put_nowait({'topic': f'hal9000/command/frontend/{topic}', 'payload': json_dumps(body)})


	def on_frontend_runlevel_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_runlevel: str, new_runlevel: str) -> bool:
		match old_runlevel:
			case HAL9000_Plugin.RUNLEVEL_UNKNOWN:
				if new_runlevel in [HAL9000_Plugin.RUNLEVEL_STARTING, \
				                    HAL9000_Plugin.RUNLEVEL_READY, \
				                    HAL9000_Plugin.RUNLEVEL_RUNNING]:
					return True
			case HAL9000_Plugin.RUNLEVEL_STARTING:
				if new_runlevel == HAL9000_Plugin.RUNLEVEL_READY:
					return True
			case HAL9000_Plugin.RUNLEVEL_READY:
				if new_runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING:
					return True
		return False


	def on_frontend_status_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_status: str, new_status: str) -> bool:
		if new_status == Action.FRONTEND_STATUS_ONLINE:
			datetime_now = datetime_datetime.now()
			epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
			synced = 'true' if self.daemon.plugins['brain'].time == 'synchronized' else 'false'
			self.send_frontend_command('application/runtime', {'time': {'epoch': epoch, 'synced': synced}})
			if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
				self.send_frontend_command('gui/screen', {'on': {}})
			else:
				self.send_frontend_command('gui/screen', {'off': {}})
		if new_status in [Action.FRONTEND_STATUS_ONLINE, Action.FRONTEND_STATUS_OFFLINE]:
			return True
		return False


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_screen: str, new_screen: str) -> bool:
		self.daemon.logger.debug(f"STATUS at screen transition = {self.daemon.plugins}")
		if old_screen == 'off' and new_screen == 'on':
			self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
			self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	async def on_frontend_signal(self, plugin: HAL9000_Plugin_Status, signal: dict) -> None:
		if 'runlevel' in signal:
			match self.daemon.plugins['frontend'].runlevel:
				case HAL9000_Plugin.RUNLEVEL_UNKNOWN:
					if signal['runlevel'] in [HAL9000_Plugin.RUNLEVEL_STARTING, \
					                          HAL9000_Plugin.RUNLEVEL_READY, \
					                          HAL9000_Plugin.RUNLEVEL_RUNNING]:
						self.daemon.plugins['frontend'].runlevel = signal['runlevel']
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					if signal['runlevel'] == HAL9000_Plugin.RUNLEVEL_READY:
						self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_READY
						self.daemon.plugins['frontend'].screen = 'none'
						self.daemon.plugins['frontend'].overlay = 'none'
				case HAL9000_Plugin.RUNLEVEL_READY:
					if signal['runlevel'] == HAL9000_Plugin.RUNLEVEL_RUNNING:
						self.daemon.plugins['frontend'].runlevel = HAL9000_Plugin.RUNLEVEL_RUNNING
		if 'status' in signal:
			match self.daemon.plugins['frontend'].status:
				case Action.FRONTEND_STATUS_ONLINE:
					if signal['status'] == Action.FRONTEND_STATUS_OFFLINE:
						self.daemon.plugins['frontend'].status = Action.FRONTEND_STATUS_OFFLINE
				case Action.FRONTEND_STATUS_OFFLINE:
					if signal['status'] == Action.FRONTEND_STATUS_ONLINE:
						self.daemon.plugins['frontend'].status = Action.FRONTEND_STATUS_ONLINE
		if 'environment' in signal:
			if 'set' in signal['environment']:
				if 'key' in signal['environment']['set'] and 'value' in signal['environment']['set']:
					key = signal['environment']['set']['key']
					value = signal['environment']['set']['value']
					self.send_frontend_command('application/environment', {'set': {'key': key, 'value': value}})
		if 'gui' in signal:
			if 'screen' in signal['gui']:
				if 'url' in signal['gui']['screen']['parameter']:
					url = signal['gui']['screen']['parameter']['url']
					url_parameter_id = ''
					url_parameter_ipv4 = await self.daemon.get_system_ipv4()
					if 'id' in signal['gui']['screen']['parameter']:
						url_parameter_id = signal['gui']['screen']['parameter']['id']
					url = url.format(id=url_parameter_id, ip_address=url_parameter_ipv4)
					signal['gui']['screen']['parameter']['url'] = url
					if 'hint' not in signal['gui']['screen']['parameter']:
						signal['gui']['screen']['parameter']['hint'] = signal['gui']['screen']['parameter']['url']
				self.daemon.plugins['frontend'].screen = signal['gui']['screen']['name']
				if 'origin' not in signal['gui']['screen'] or signal['gui']['screen']['origin'] != 'arduino':
					self.send_frontend_command('gui/screen', {signal['gui']['screen']['name']: signal['gui']['screen']['parameter']})
			if 'overlay' in signal['gui']:
				self.daemon.plugins['frontend'].overlay = signal['gui']['overlay']['name']
				if 'origin' not in signal['gui']['overlay'] or signal['gui']['overlay']['origin'] != 'arduino':
					self.send_frontend_command('gui/overlay', {signal['gui']['overlay']['name']: signal['gui']['overlay']['parameter']})


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_runlevel: str, new_runlevel: str) -> bool:
#TODO		match new_runlevel:
#TODO			case HAL9000_Plugin.RUNLEVEL_READY:
#TODO				if self.daemon.config['brain:require-synced-time'] is True and self.daemon.plugins['brain'].time != 'synchronized':
#TODO					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'splash',
#TODO					                                                         'parameter': {'id': 'NTP',
#TODO					                                                                       'url': self.daemon.config['help:splash-url'],
#TODO					                                                                       'message': 'Waiting for NTP sync...'}}}})
#TODO					self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_status: str, new_status: str) -> bool:
		match new_status:
			case Daemon.BRAIN_STATUS_AWAKE:
				if old_status == HAL9000_Plugin_Status.UNINITIALIZED:
					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
					self.daemon.schedule_signal(2, 'frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop',
					                                                                    'value': 'false'}}},
					                            'frontend:gui/screen#animations/loop:timeout')
				else:
					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'on', 'parameter': {}}}})
			case Daemon.BRAIN_STATUS_ASLEEP:
				self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'off', 'parameter': {}}}})
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_time: str, new_time: str) -> bool:
		datetime_now = datetime_datetime.now()
		epoch = int(datetime_now.timestamp() + datetime_now.astimezone().tzinfo.utcoffset(None).seconds)
		synced = 'true' if new_time == 'synchronized' else 'false'
		self.send_frontend_command('application/runtime', {'time': {'epoch': epoch, 'synced': synced}})
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin_Status, signal: dict) -> None:
		if 'runlevel' in signal:
			if signal['runlevel'] in [None, False, '', {}]:
				self.daemon.mqtt_publish_queue.put_nowait({'topic': self.config['frontend-runlevel-mqtt-topic'], 'payload': ''})


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_status: str, new_status: str) -> bool:
		if old_status == Kalliope_Action.KALLIOPE_STATUS_WAITING and new_status == Kalliope_Action.KALLIOPE_STATUS_LISTENING:
			self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'animations', 'parameter': {'name': 'hal9000'}}}})
		if old_status == Kalliope_Action.KALLIOPE_STATUS_SPEAKING and new_status == Kalliope_Action.KALLIOPE_STATUS_WAITING:
			self.daemon.queue_signal('frontend', {'environment': {'set': {'key': 'gui/screen:animations/loop', 'value': 'false'}}})
		return True

