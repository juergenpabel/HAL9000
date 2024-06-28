import os
import json
import configparser
from datetime import datetime

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin_Cortex
from hal9000.brain.daemon import Daemon
from hal9000.brain.plugins.kalliope.action import Action as Kalliope_Action

from dbus_fast.aio import MessageBus
from dbus_fast.auth import AuthExternal, UID_NOT_SPECIFIED
from dbus_fast.constants import BusType
import asyncio

async def ipaddress():
	bus = await MessageBus(None, BusType.SYSTEM, AuthExternal(UID_NOT_SPECIFIED)).connect()
	introspection = await bus.introspect('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager')
	obj = bus.get_proxy_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager', introspection)
	nm = obj.get_interface('org.freedesktop.NetworkManager')
	for connection in await nm.get_active_connections():
		introspection2 = await bus.introspect('org.freedesktop.NetworkManager', connection)
		obj2 = bus.get_proxy_object('org.freedesktop.NetworkManager', connection, introspection2)
		conf = obj2.get_interface('org.freedesktop.NetworkManager.Connection.Active')
		if await conf.get_default() is True:
			ip4config = await conf.get_ip4_config()
			introspection3 = await bus.introspect('org.freedesktop.NetworkManager', ip4config)
			obj3 = bus.get_proxy_object('org.freedesktop.NetworkManager', ip4config, introspection3)
			data= obj3.get_interface('org.freedesktop.NetworkManager.IP4Config')
			address_data = await data.get_address_data()
			return address_data[0]['address'].value
	return '127.0.0.1'



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


	def configure(self, configuration: configparser.ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['frontend-status-mqtt-topic'] = configuration.get(section_name, 'frontend-status-mqtt-topic', fallback='hal9000/command/frontend/status')
		self.daemon.cortex['plugin']['frontend'].state = Action.FRONTEND_STATE_UNKNOWN
		self.daemon.cortex['plugin']['frontend'].addNameCallback(self.on_frontend_state_callback, 'state')
		self.daemon.cortex['plugin']['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.cortex['plugin']['frontend'].addSignalHandler(self.on_frontend_signal)
		self.daemon.cortex['plugin']['kalliope'].addNameCallback(self.on_kalliope_state_callback, 'state')
		self.daemon.cortex['plugin']['brain'].addNameCallback(self.on_brain_state_callback, 'state')
		self.daemon.cortex['plugin']['brain'].addNameCallback(self.on_brain_consciousness_callback, 'consciousness')
		self.daemon.cortex['plugin']['brain'].addSignalHandler(self.on_brain_signal)


	def runlevel(self) -> str:
		if self.daemon.cortex['plugin']['frontend'].state in [Action.FRONTEND_STATE_UNKNOWN, Action.FRONTEND_STATE_STARTING]:
			return self.daemon.cortex['plugin']['frontend'].state
		return Action.PLUGIN_RUNLEVEL_RUNNING


	def runlevel_error(self) -> dict:
		return {'code': '01',
		        'level': 'error',
		        'message': "No connection to microcontroller."}


	def send_command(self, topic, body) -> None:
		self.daemon.mqtt.publish(f'hal9000/command/frontend/{topic}', body)


	def send_system_time(self, synced: bool = False):
		body = {'time': {'epoch': int(datetime.now().timestamp() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds), 'synced': synced}}
		self.send_command('application/runtime', json.dumps(body));


	def on_frontend_state_callback(self, plugin, key, old_value, new_value):
		if new_value == 'ready':
			self.daemon.set_system_time()
		return True ##todo validity check


	def on_frontend_screen_callback(self, plugin, key, old_value, new_value):
		if new_value == 'idle':
			if len(self.error_queue) > 0:
				error = error_queue.pop(0)
				self.daemon.video_gui_screen_show('error', {'code': error.code, 'url': error.url, 'message': error.message}, error.timeout)
		return True


	def on_frontend_signal(self, plugin, signal):
		if 'state' in signal:
			self.daemon.cortex['plugin']['frontend'].state = signal['state']
			if signal['state'] == 'ready':
				self.send_command('application/runtime', json.dumps({'condition': self.daemon.cortex['plugin']['brain'].consciousness}))
		if 'gui' in signal:
			if 'screen' in signal['gui']:
				if 'url' in signal['gui']['screen']['parameter']:
					url = signal['gui']['screen']['parameter']['url']
					url_parameter_code = ''
					url_parameter_ipaddress = asyncio.run(ipaddress())
					if 'code' in signal['gui']['screen']['parameter']:
						url_parameter_code = signal['gui']['screen']['parameter']['code']
					url = url.format(ip_address=url_parameter_ipaddress, code=url_parameter_code)
					signal['gui']['screen']['parameter']['url'] = url
					if 'hint' not in signal['gui']['screen']['parameter']:
						signal['gui']['screen']['parameter']['hint'] = signal['gui']['screen']['parameter']['url']
				self.daemon.cortex['plugin']['frontend'].screen = signal['gui']['screen']['name']
				self.send_command('gui/screen', json.dumps({signal['gui']['screen']['name']: signal['gui']['screen']['parameter']}))
			if 'overlay' in signal['gui']:
				self.daemon.cortex['plugin']['frontend'].overlay = signal['gui']['overlay']['name']
				self.send_command('gui/overlay', json.dumps({signal['gui']['overlay']['name']: signal['gui']['overlay']['parameter']}))


	def on_brain_state_callback(self, plugin, key, old_value, new_value):
		if new_value == 'ready':
			if self.daemon.cortex['plugin']['brain'].consciousness == 'awake':
				self.daemon.cortex['plugin']['frontend'].screen = 'none'
				self.daemon.cortex['plugin']['frontend'].overlay = 'none'
				self.daemon.video_gui_screen_show('hal9000', {'queue': 'replace', 'sequence': {'name': 'wakeup', 'loop': 'false'}})
				self.daemon.video_gui_screen_show('hal9000', {'queue': 'append',  'sequence': {'name': 'active', 'loop': 'false'}})
				self.daemon.video_gui_screen_show('hal9000', {'queue': 'append',  'sequence': {'name': 'active', 'loop': 'false'}})
				self.daemon.video_gui_screen_show('hal9000', {'queue': 'append',  'sequence': {'name': 'sleep',  'loop': 'false'}})
		return True


	def on_brain_consciousness_callback(self, plugin, key, old_value, new_value):
		if self.daemon.cortex['plugin']['brain'].state == 'ready':
			self.send_command('application/runtime', json.dumps({'condition': new_value}))
			match new_value:
				case 'awake':
					self.daemon.cortex['plugin']['frontend'].screen = 'idle'
					self.daemon.cortex['plugin']['frontend'].overlay = 'none'
				case 'asleep':
					self.daemon.cortex['plugin']['frontend'].screen = 'none'
					self.daemon.cortex['plugin']['frontend'].overlay = 'none'
		return True


	def on_brain_signal(self, plugin, signal):
		if 'status' in signal:
			self.daemon.mqtt.publish(self.config['frontend-status-mqtt-topic'], json.dumps(signal['status']))
		if 'time' in signal:
			synced = False
			if 'synced' in signal['time']:
				synced = bool(signal['time']['synced'])
			self.send_system_time(synced)


	def on_kalliope_state_callback(self, plugin, key, old_value, new_value):
		if old_value == Kalliope_Action.KALLIOPE_STATE_SPEAKING and new_value == Kalliope_Action.KALLIOPE_STATE_WAITING:
			self.daemon.video_gui_screen_show('hal9000', {'queue': 'replace', 'sequence': {'name': 'sleep',  'loop': 'false'}}, 3)
		if old_value == Kalliope_Action.KALLIOPE_STATE_WAITING and new_value == Kalliope_Action.KALLIOPE_STATE_LISTENING:
			self.daemon.video_gui_screen_show('hal9000', {'queue': 'replace', 'sequence': {'name': 'wakeup', 'loop': 'false'}})
			self.daemon.video_gui_screen_show('hal9000', {'queue': 'append',  'sequence': {'name': 'active', 'loop': 'true'}})
		return True

