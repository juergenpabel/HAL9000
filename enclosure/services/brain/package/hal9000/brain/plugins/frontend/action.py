from json import dumps as json_dumps
from os.path import exists as os_path_exists
from datetime import datetime as datetime_datetime, \
                     timedelta as datetime_timedelta
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin_Status
from hal9000.brain.daemon import Daemon
from hal9000.brain.plugins.kalliope.action import Action as Kalliope_Action


class Action(HAL9000_Action):

	FRONTEND_STATUS_UNKNOWN  = 'unknown'
	FRONTEND_STATUS_STARTING = 'starting'
	FRONTEND_STATUS_READY    = 'ready'
	FRONTEND_STATUS_OFFLINE  = 'offline'
	FRONTEND_STATUS_ONLINE   = 'online'


	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Status, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'frontend', action_name, plugin_status, **kwargs)
		self.daemon.plugins['frontend'].addNames(['screen', 'overlay', 'time'])
		self.datetime_next_time_sync = datetime_datetime.now()


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['frontend-status-mqtt-topic'] = configuration.get(section_name, 'frontend-status-mqtt-topic', fallback='hal9000/command/frontend/status')
		self.daemon.plugins['frontend'].status = Action.FRONTEND_STATUS_UNKNOWN
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_status_callback, 'status')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.plugins['frontend'].addSignalHandler(self.on_frontend_signal)
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.daemon.plugins['brain'].addSignalHandler(self.on_brain_signal)


	def runlevel(self) -> str:
		if self.daemon.plugins['frontend'].status in [Action.FRONTEND_STATUS_UNKNOWN, Action.FRONTEND_STATUS_STARTING]:
			return self.daemon.plugins['frontend'].status
		return Action.PLUGIN_RUNLEVEL_RUNNING


	def runlevel_error(self) -> dict:
		return {'code': '01',
		        'level': 'error',
		        'message': "No connection to microcontroller."}


	def send_frontend_command(self, topic:str , body: dict) -> None:
		self.daemon.mqtt_publish_queue.put_nowait({'topic': f'hal9000/command/frontend/{topic}', 'payload': json_dumps(body)})


	def on_frontend_status_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_status: str, new_status: str) -> bool:
		match old_status:
			case Action.FRONTEND_STATUS_UNKNOWN:
				if new_status in [Action.FRONTEND_STATUS_STARTING, Action.FRONTEND_STATUS_READY,
				                  Action.FRONTEND_STATUS_ONLINE, Action.FRONTEND_STATUS_OFFLINE]:
					return True
			case Action.FRONTEND_STATUS_STARTING:
				if new_status == Action.FRONTEND_STATUS_READY:
					return True
			case Action.FRONTEND_STATUS_READY | \
			     Action.FRONTEND_STATUS_ONLINE | \
			     Action.FRONTEND_STATUS_OFFLINE:
				if new_status in [Action.FRONTEND_STATUS_ONLINE, Action.FRONTEND_STATUS_OFFLINE]:
					return True
		return False


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_screen: str, new_screen: str) -> bool:
		self.daemon.logger.debug(f"STATUS at screen transition = {self.daemon.plugins}")
		return True


	async def on_frontend_signal(self, plugin: HAL9000_Plugin_Status, signal: dict) -> None:
		if 'status' in signal:
			match self.daemon.plugins['frontend'].status:
				case Action.FRONTEND_STATUS_UNKNOWN:
					if signal['status'] in [Action.FRONTEND_STATUS_STARTING, Action.FRONTEND_STATUS_READY, \
					                        Action.FRONTEND_STATUS_ONLINE, Action.FRONTEND_STATUS_OFFLINE]:
						self.daemon.plugins['frontend'].status = signal['status']
				case Action.FRONTEND_STATUS_STARTING:
					if signal['status'] == Action.FRONTEND_STATUS_READY:
						self.daemon.plugins['frontend'].status = signal['status']
						self.daemon.plugins['frontend'].screen = 'none'
						self.daemon.plugins['frontend'].overlay = 'none'
				case Action.FRONTEND_STATUS_READY:
					if signal['status'] in [Action.FRONTEND_STATUS_ONLINE, Action.FRONTEND_STATUS_OFFLINE]:
						self.daemon.plugins['frontend'].status = signal['status']
				case Action.FRONTEND_STATUS_ONLINE:
					if signal['status'] == Action.FRONTEND_STATUS_OFFLINE:
						self.daemon.plugins['frontend'].status = signal['status']
						if self.daemon.plugins['brain'].status in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP]:
							self.send_frontend_command('application/runtime', {'condition': self.daemon.plugins['brain'].status})
				case Action.FRONTEND_STATUS_OFFLINE:
					if signal['status'] == Action.FRONTEND_STATUS_ONLINE:
						self.daemon.plugins['frontend'].status = signal['status']
						if self.daemon.plugins['brain'].status in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP]:
							self.send_frontend_command('application/runtime', {'condition': self.daemon.plugins['brain'].status})
		if 'time' in signal:
			datetime_now = datetime_datetime.now()
			if datetime_now > self.datetime_next_time_sync:
				time_synchronized = os_path_exists('/run/systemd/timesync/synchronized')
				self.daemon.plugins['frontend'].time = 'synchronized' if time_synchronized is True else 'unsynchronized'
				epoch = int(datetime_now.timestamp() + datetime_datetime.now().astimezone().tzinfo.utcoffset(None).seconds)
				self.send_frontend_command('application/runtime', {'time': {'epoch': epoch, 'synced': time_synchronized}})
				self.datetime_next_time_sync = datetime_now + datetime_timedelta(seconds=1 if time_synchronized is False else 3600)
		if 'gui' in signal:
			if 'screen' in signal['gui']:
				if 'url' in signal['gui']['screen']['parameter']:
					url = signal['gui']['screen']['parameter']['url']
					url_parameter_code = ''
					url_parameter_ipv4 = await self.daemon.get_system_ipv4()
					if 'code' in signal['gui']['screen']['parameter']:
						url_parameter_code = signal['gui']['screen']['parameter']['code']
					url = url.format(ip_address=url_parameter_ipv4, code=url_parameter_code)
					signal['gui']['screen']['parameter']['url'] = url
					if 'hint' not in signal['gui']['screen']['parameter']:
						signal['gui']['screen']['parameter']['hint'] = signal['gui']['screen']['parameter']['url']
				self.daemon.plugins['frontend'].screen = signal['gui']['screen']['name']
				self.send_frontend_command('gui/screen', {signal['gui']['screen']['name']: signal['gui']['screen']['parameter']})
			if 'overlay' in signal['gui']:
				self.daemon.plugins['frontend'].overlay = signal['gui']['overlay']['name']
				self.send_frontend_command('gui/overlay', {signal['gui']['overlay']['name']: signal['gui']['overlay']['parameter']})


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_status: str, new_status: str) -> bool:
		match new_status:
			case Daemon.BRAIN_STATUS_READY:
				self.daemon.queue_signal('frontend', {'time': {}})
				self.daemon.schedule_signal(1, 'frontend', {'time': {}}, 'frontend:time', 'interval')
			case Daemon.BRAIN_STATUS_AWAKE:
				self.send_frontend_command('application/runtime', {'condition': 'awake'})
				if old_status == Daemon.BRAIN_STATUS_READY:
					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
					                                                         'parameter': {'queue': 'replace',
					                                                                       'sequence': {'name': 'wakeup', 'loop': 'false'}}}}})
					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
					                                                         'parameter': {'queue': 'append',
					                                                                       'sequence': {'name': 'active', 'loop': 'false'}}}}})
					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
					                                                         'parameter': {'queue': 'append',
					                                                                       'sequence': {'name': 'active', 'loop': 'false'}}}}})
					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
					                                                         'parameter': {'queue': 'append',
					                                                                       'sequence': {'name': 'sleep', 'loop': 'false'}}}}})
				else:
					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
				self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
			case Daemon.BRAIN_STATUS_ASLEEP:
				self.send_frontend_command('application/runtime', {'condition': 'asleep'})
				self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'none', 'parameter': {}}}})
				self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}})
			case Daemon.BRAIN_STATUS_DYING:
				self.send_frontend_command('application/runtime', {'condition': 'zombie'})
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin_Status, signal: dict) -> None:
		if 'status' in signal and signal['status'] in [None, False, '', {}]:
			self.daemon.mqtt_publish_queue.put_nowait({'topic': self.config['frontend-status-mqtt-topic'], 'payload': ''})


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_status: str, new_status: str) -> bool:
		if old_status == Kalliope_Action.KALLIOPE_STATUS_SPEAKING and new_status == Kalliope_Action.KALLIOPE_STATUS_WAITING:
			self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
			                                                         'parameter': {'queue': 'replace',
			                                                                       'sequence': {'name': 'sleep', 'loop': 'false'}}}}})
		if old_status == Kalliope_Action.KALLIOPE_STATUS_WAITING and new_status == Kalliope_Action.KALLIOPE_STATUS_LISTENING:
			self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
			                                                         'parameter': {'queue': 'replace',
			                                                                       'sequence': {'name': 'wakeup', 'loop': 'false'}}}}})
			self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
			                                                         'parameter': {'queue': 'append',
			                                                                       'sequence': {'name': 'active', 'loop': 'true'}}}}})
		# the following is for kalliope STT error cases (hal9000-on-stt-error & hal9000-on-order-not-found)
		if old_status == Kalliope_Action.KALLIOPE_STATUS_THINKING and new_status == Kalliope_Action.KALLIOPE_STATUS_WAITING:
			self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
			                                                         'parameter': {'queue': 'replace',
			                                                                       'sequence': {'name': 'active', 'loop': 'false'}}}}})
			self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
			                                                         'parameter': {'queue': 'append',
			                                                                       'sequence': {'name': 'active', 'loop': 'false'}}}}})
			self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
			                                                         'parameter': {'queue': 'append',
			                                                                       'sequence': {'name': 'sleep', 'loop': 'false'}}}}})
		return True

