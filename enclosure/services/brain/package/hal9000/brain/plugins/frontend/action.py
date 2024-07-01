from json import dumps as json_dumps
from os.path import exists as os_path_exists
from datetime import datetime as datetime_datetime
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin_Cortex
from hal9000.brain.daemon import Daemon
from hal9000.brain.plugins.kalliope.action import Action as Kalliope_Action


class Action(HAL9000_Action):

	FRONTEND_STATE_UNKNOWN  = 'unknown'
	FRONTEND_STATE_STARTING = 'starting'
	FRONTEND_STATE_READY    = 'ready'
	FRONTEND_STATE_OFFLINE  = 'offline'
	FRONTEND_STATE_ONLINE   = 'online'
	FRONTEND_STATES_VALID = [FRONTEND_STATE_STARTING, FRONTEND_STATE_READY, FRONTEND_STATE_OFFLINE, FRONTEND_STATE_ONLINE]


	def __init__(self, action_name: str, plugin_cortex: HAL9000_Plugin_Cortex, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'frontend', action_name, plugin_cortex, **kwargs)
		self.daemon.cortex['plugin']['frontend'].addNames(['screen', 'overlay'])
		self.error_queue = list()


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['frontend-status-mqtt-topic'] = configuration.get(section_name, 'frontend-status-mqtt-topic', fallback='hal9000/command/frontend/status')
		self.daemon.cortex['plugin']['frontend'].state = Action.FRONTEND_STATE_UNKNOWN
		self.daemon.cortex['plugin']['frontend'].addNameCallback(self.on_frontend_state_callback, 'state')
		self.daemon.cortex['plugin']['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.cortex['plugin']['frontend'].addSignalHandler(self.on_frontend_signal)
		self.daemon.cortex['plugin']['kalliope'].addNameCallback(self.on_kalliope_state_callback, 'state')
		self.daemon.cortex['plugin']['brain'].addNameCallback(self.on_brain_state_callback, 'state')
		self.daemon.cortex['plugin']['brain'].addSignalHandler(self.on_brain_signal)


	def runlevel(self) -> str:
		if self.daemon.cortex['plugin']['frontend'].state in [Action.FRONTEND_STATE_UNKNOWN, Action.FRONTEND_STATE_STARTING]:
			return self.daemon.cortex['plugin']['frontend'].state
		return Action.PLUGIN_RUNLEVEL_RUNNING


	def runlevel_error(self) -> dict:
		return {'code': '01',
		        'level': 'error',
		        'message': "No connection to microcontroller."}


	def send_frontend_command(self, topic:str , body: dict) -> None:
		self.daemon.mqtt_publish_queue.put_nowait({'topic': f'hal9000/command/frontend/{topic}', 'payload': json_dumps(body)})


	def on_frontend_state_callback(self, plugin, key, old_state, new_state):
		if old_state in [Action.FRONTEND_STATE_UNKNOWN, Action.FRONTEND_STATE_STARTING]:
			if new_state not in [Action.FRONTEND_STATE_STARTING, Action.FRONTEND_STATE_READY]:
				return False
		if old_state in [Action.FRONTEND_STATE_READY, Action.FRONTEND_STATE_ONLINE, Action.FRONTEND_STATE_OFFLINE]:
			if new_state not in [Action.FRONTEND_STATE_ONLINE, Action.FRONTEND_STATE_OFFLINE]:
				return False
		if new_state == Action.FRONTEND_STATE_READY:
			self.daemon.add_signal('frontend', {'time': None})
			self.daemon.add_signal('frontend', {'state': None})
			self.daemon.cortex['plugin']['frontend'].screen = 'none'
			self.daemon.cortex['plugin']['frontend'].overlay = 'none'
		return True


	def on_frontend_screen_callback(self, plugin, key, old_screen, new_screen):
		if new_screen == 'idle':
			if len(self.error_queue) > 0:
				error = error_queue.pop(0)
				self.daemon.add_signal('frontend', {'gui': {'screen': {'name': 'error',
				                                                       'parameter': {'code': error.code,
				                                                                     'url': error.url,
				                                                                     'message': error.message}}}})
				if error.timeout is not None:
					self.daemon.add_timeout(error.timeout, 'frontend:gui/screen', {'name': 'idle', 'parameter': {}})

		return True


	async def on_frontend_signal(self, plugin, signal):
		if 'state' in signal:
			if self.daemon.cortex['plugin']['frontend'].state in [Action.FRONTEND_STATE_UNKNOWN, Action.FRONTEND_STATE_STARTING]:
				if signal['state'] in [Action.FRONTEND_STATE_STARTING, Action.FRONTEND_STATE_READY]:
					self.daemon.cortex['plugin']['frontend'].state = signal['state']
					return
			if self.daemon.cortex['plugin']['frontend'].state in [Action.FRONTEND_STATE_READY, Action.FRONTEND_STATE_ONLINE, Action.FRONTEND_STATE_OFFLINE]:
				if signal['state'] in [Action.FRONTEND_STATE_ONLINE, Action.FRONTEND_STATE_OFFLINE]:
					self.daemon.cortex['plugin']['frontend'].state = signal['state']
					if self.daemon.cortex['plugin']['brain'].state in [Daemon.BRAIN_STATE_AWAKE, Daemon.BRAIN_STATE_ASLEEP]:
						self.send_frontend_command('application/runtime', {'condition': self.daemon.cortex['plugin']['brain'].state})
					return
		if 'time' in signal:
			epoch = int(datetime_datetime.now().timestamp() + datetime_datetime.now().astimezone().tzinfo.utcoffset(None).seconds)
			synced = os_path_exists('/run/systemd/timesync/synchronized')
			self.send_frontend_command('application/runtime', {'time': {'epoch': epoch, 'synced': synced}})
			self.daemon.add_timeout(3600 if synced is True else 60, 'plugin:signal', {'plugin': 'frontend', 'signal': {'time': None}})
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
				self.daemon.cortex['plugin']['frontend'].screen = signal['gui']['screen']['name']
				self.send_frontend_command('gui/screen', {signal['gui']['screen']['name']: signal['gui']['screen']['parameter']})
			if 'overlay' in signal['gui']:
				self.daemon.cortex['plugin']['frontend'].overlay = signal['gui']['overlay']['name']
				self.send_frontend_command('gui/overlay', {signal['gui']['overlay']['name']: signal['gui']['overlay']['parameter']})


	def on_brain_state_callback(self, plugin, key, old_state, new_state):
		match new_state:
			case Daemon.BRAIN_STATE_READY:
				pass # TODO
			case Daemon.BRAIN_STATE_AWAKE:
				self.send_frontend_command('application/runtime', {'condition': 'awake'})
				if old_state == Daemon.BRAIN_STATE_READY:
					self.daemon.add_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
					                                                       'parameter': {'queue': 'replace',
					                                                                     'sequence': {'name': 'wakeup', 'loop': 'false'}}}}})
					self.daemon.add_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
					                                                       'parameter': {'queue': 'append',
					                                                                     'sequence': {'name': 'active', 'loop': 'false'}}}}})
					self.daemon.add_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
					                                                       'parameter': {'queue': 'append',
					                                                                     'sequence': {'name': 'active', 'loop': 'false'}}}}})
					self.daemon.add_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
					                                                       'parameter': {'queue': 'append',
					                                                                     'sequence': {'name': 'sleep', 'loop': 'false'}}}}})
				else:
					self.daemon.cortex['plugin']['frontend'].screen = 'idle'
				self.daemon.cortex['plugin']['frontend'].overlay = 'none'
			case Daemon.BRAIN_STATE_ASLEEP:
				self.send_frontend_command('application/runtime', {'condition': 'asleep'})
				self.daemon.cortex['plugin']['frontend'].screen = 'none'
				self.daemon.cortex['plugin']['frontend'].overlay = 'none'
			case Daemon.BRAIN_STATE_DYING:
				pass
			case _:
				print("TODO:on_brain_state_callback")
		return True


	async def on_brain_signal(self, plugin, signal):
		if 'status' in signal:
			self.daemon.mqtt_publish_queue.put_nowait({'topic': self.config['frontend-status-mqtt-topic'], 'payload': json_dumps(signal['status'])})


	def on_kalliope_state_callback(self, plugin, key, old_state, new_state):
		if old_state == Kalliope_Action.KALLIOPE_STATE_SPEAKING and new_state == Kalliope_Action.KALLIOPE_STATE_WAITING:
			self.daemon.add_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
			                                                       'parameter': {'queue': 'replace',
			                                                                     'sequence': {'name': 'sleep', 'loop': 'false'}}}}})
		if old_state == Kalliope_Action.KALLIOPE_STATE_WAITING and new_state == Kalliope_Action.KALLIOPE_STATE_LISTENING:
			self.daemon.add_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
			                                                       'parameter': {'queue': 'replace',
			                                                                     'sequence': {'name': 'wakeup', 'loop': 'false'}}}}})
			self.daemon.add_signal('frontend', {'gui': {'screen': {'name': 'hal9000',
			                                                       'parameter': {'queue': 'append',
			                                                                     'sequence': {'name': 'active', 'loop': 'true'}}}}})
		return True

