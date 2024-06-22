#!/usr/bin/python3

import os
import json
import configparser
from datetime import datetime

from hal9000.brain.modules import HAL9000_Action
from hal9000.brain.daemon import Daemon

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
	FRONTEND_STATE_OFFLINE  = 'offline'
	FRONTEND_STATE_ONLINE   = 'online'
	FRONTEND_STATES_VALID = [FRONTEND_STATE_STARTING, FRONTEND_STATE_OFFLINE, FRONTEND_STATE_ONLINE]


	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'frontend', action_name, **kwargs)
		self.error_queue = list()


	def configure(self, configuration: configparser.ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		self.config['frontend-status-mqtt-topic'] = configuration.get(section_name, 'frontend-status-mqtt-topic', fallback='hal9000/command/frontend/status')
		cortex['service']['frontend'].state = Action.FRONTEND_STATE_UNKNOWN
		cortex['service']['frontend'].screen = 'idle'
		cortex['service']['frontend'].overlay = 'none'
		cortex['service']['frontend'].addCallback(self.on_frontend_activity)


	def runlevel(self, cortex: dict) -> str:
		if cortex['service']['frontend'].state in [Action.FRONTEND_STATE_UNKNOWN, Action.FRONTEND_STATE_STARTING]:
			return cortex['service']['frontend'].state
		return Action.MODULE_RUNLEVEL_RUNNING


	def runlevel_error(self, cortex: dict) -> dict:
		return {'code': '01',
		        'level': 'error',
		        'message': "No connection to microcontroller."}


	def process(self, signal: dict, cortex: dict) -> None:
		if 'brain' in signal:
			if 'ready' in signal['brain']:
				self.daemon.video_gui_screen_show('hal9000', {'queue': 'replace', 'sequence': {'name': 'wakeup', 'loop': 'false'}})
				self.daemon.video_gui_screen_show('hal9000', {'queue': 'append',  'sequence': {'name': 'active', 'loop': 'false'}})
				self.daemon.video_gui_screen_show('hal9000', {'queue': 'append',  'sequence': {'name': 'active', 'loop': 'false'}})
				self.daemon.video_gui_screen_show('hal9000', {'queue': 'append',  'sequence': {'name': 'sleep',  'loop': 'false'}}, 5)
			if 'status' in signal['brain']:
				self.daemon.mqtt.publish(self.config['frontend-status-mqtt-topic'], json.dumps(signal['brain']['status']))
			if 'consciousness' in signal['brain']:
				self.send_command('application/runtime', json.dumps({'condition': signal['brain']['consciousness']}))
			if 'time' in signal['brain']:
				synced = False
				if 'synced' in signal['brain']['time']:
					synced = bool(signal['brain']['time']['synced'])
				self.send_system_time(synced)
		if 'frontend' in signal:
			if 'state' in signal['frontend']:
				frontend_state = signal['frontend']['state']
				if frontend_state in Action.FRONTEND_STATES_VALID:
					cortex['service']['frontend'].state = frontend_state
					if frontend_state == 'online':
						self.daemon.set_system_time()
			if 'gui' in signal['frontend']:
				if 'screen' in signal['frontend']['gui']:
					if 'url' in signal['frontend']['gui']['screen']['parameter']:
						url = signal['frontend']['gui']['screen']['parameter']['url']
						parameter_code = ''
						parameter_ipaddress = asyncio.run(ipaddress())
						if 'code' in signal['frontend']['gui']['screen']['parameter']:
							parameter_code = signal['frontend']['gui']['screen']['parameter']['code']
						url = url.format(ip_address=parameter_ipaddress, code=parameter_code)
						signal['frontend']['gui']['screen']['parameter']['url'] = url
					if 'hint' not in signal['frontend']['gui']['screen']['parameter']:
						signal['frontend']['gui']['screen']['parameter']['hint'] = signal['frontend']['gui']['screen']['parameter']['url']
					self.daemon.video_gui_screen_show(signal['frontend']['gui']['screen']['name'], signal['frontend']['gui']['screen']['parameter'])
				if 'overlay' in signal['frontend']['gui']:
					self.daemon.video_gui_overlay_show(signal['frontend']['gui']['screen']['name'], signal['frontend']['gui']['screen']['parameter'])
			if 'error' in signal['frontend']:
				code = signal['frontend']['error']['code']
				message = signal['frontend']['error']['message']
				timeout = None
				if 'timeout' in signal['frontend']['error']:
					timeout = int(signal['frontend']['error']['timeout'])
				if cortex['service']['frontend'].screen == 'idle':
					self.daemon.video_gui_screen_show('error', {'code': code,
					                                            'url': self.daemon.config['help:error-url'].format(code=code),
					                                            'message': message},
					                                  timeout)
				else:
					self.error_queue.append({'code': code,
					                         'url': self.daemon.config['help:error-url'].format(code=code),
					                         'message': message,
					                         'timeout': timeout})


	def send_command(self, topic, body) -> None:
		self.daemon.mqtt.publish(f'hal9000/command/frontend/{topic}', body)


	def send_system_time(self, synced: bool = False):
		body = {'time': {'epoch': int(datetime.now().timestamp() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds), 'synced': synced}}
		self.send_command('application/runtime', json.dumps(body));


	def on_frontend_activity(self, module, name, old_value, new_value):
		if self.daemon.cortex['service']['frontend'].state != Action.FRONTEND_STATE_ONLINE:
			if name == 'state':
				return True
			return False
		if name == 'signal':
			if 'signal' in new_value:
				if 'gui' in new_value['signal']:
					if 'screen' in new_value['signal']['gui']:
						screen = new_value['signal']['gui']['screen']['name']
						parameter = new_value['signal']['gui']['screen']['parameter']
						self.send_command('gui/screen', json.dumps({screen: parameter}))
					if 'overlay' in new_value['signal']['gui']:
						overlay = new_value['signal']['gui']['overlay']['name']
						parameter = new_value['signal']['gui']['overlay']['parameter']
						self.send_command('gui/overlay', json.dumps({overlay: parameter}))
		if name == 'screen' and new_value == 'idle':
			if len(self.error_queue) > 0:
				error = error_queue.pop(0)
				self.daemon.video_gui_screen_show('error', {'code': error.code, 'url': error.url, 'message': error.message}, error.timeout)
		return True
