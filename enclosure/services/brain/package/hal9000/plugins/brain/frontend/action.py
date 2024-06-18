#!/usr/bin/python3

import os
import json
import configparser
from datetime import datetime

from hal9000.brain.modules import HAL9000_Action
from hal9000.brain.daemon import Daemon


class Action(HAL9000_Action):

	FRONTEND_STATE_UNKNOWN  = 'unknown'
	FRONTEND_STATE_STARTING = 'starting'
	FRONTEND_STATE_OFFLINE  = 'offline'
	FRONTEND_STATE_ONLINE   = 'online'
	FRONTEND_STATES_VALID = [FRONTEND_STATE_STARTING, FRONTEND_STATE_OFFLINE, FRONTEND_STATE_ONLINE]


	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'frontend', action_name, **kwargs)
		self.error_queue = list()
		self.daemon.cortex['#activity']['video'].addCallback(self.on_video_activity)


	def configure(self, configuration: configparser.ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		self.config['frontend-status-mqtt-topic'] = configuration.get(section_name, 'frontend-status-mqtt-topic', fallback='hal9000/command/frontend/status')
		cortex['frontend'] = dict()
		cortex['frontend']['state'] = Action.FRONTEND_STATE_UNKNOWN


	def runlevel(self, cortex: dict) -> str:
		if cortex['frontend']['state'] in [Action.FRONTEND_STATE_UNKNOWN, Action.FRONTEND_STATE_STARTING]:
			return cortex['frontend']['state']
		return Action.MODULE_RUNLEVEL_RUNNING


	def runlevel_error(self, cortex: dict) -> dict:
		return {'code': '01',
		        'level': 'fatal',
		        'message': "No connection to microcontroller. Display and inputs/sensors will not work.",
		        'audio': 'error/001-frontend.wav'}


	def process(self, signal: dict, cortex: dict) -> None:
		if 'brain' in signal:
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
					cortex['frontend']['state'] = frontend_state
					if frontend_state == 'online':
						self.daemon.set_system_time()
			if 'gui' in signal['frontend']:
				if 'screen' in signal['frontend']['gui']:
					if 'url' in signal['frontend']['gui']['screen']['parameter']:
						url = signal['frontend']['gui']['screen']['parameter']['url']
						data_code = ''
						data_ip = '127.0.0.1'
						try:
							import socket
							s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
							s.connect(('1.1.1.1', 1))
							data_ip = s.getsockname()[0]
						except:
							pass
						finally:
							s.close()
						if 'code' in signal['frontend']['gui']['screen']['parameter']:
							data_code = signal['frontend']['gui']['screen']['parameter']['code']
						url = url.format(ip_address=data_ip, code=data_code)
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
				if cortex['#activity']['video'].screen == 'idle':
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


	def on_video_activity(self, target, item, old_value, new_value):
		if self.daemon.cortex['frontend']['state'] != Action.FRONTEND_STATE_ONLINE:
			return False
		if item == 'signal':
			if 'activity' in new_value:
				if 'gui' in new_value['activity']:
					if 'screen' in new_value['activity']['gui']:
						screen = new_value['activity']['gui']['screen']['name']
						parameter = new_value['activity']['gui']['screen']['parameter']
						self.send_command('gui/screen', json.dumps({screen: parameter}))
					if 'overlay' in new_value['activity']['gui']:
						overlay = new_value['activity']['gui']['overlay']['name']
						parameter = new_value['activity']['gui']['overlay']['parameter']
						self.send_command('gui/overlay', json.dumps({overlay: parameter}))
		if item == 'screen' and new_value == 'idle':
			if len(self.error_queue) > 0:
				error = error_queue.pop(0)
				self.daemon.video_gui_screen_show('error', {'code': error.code, 'url': error.url, 'message': error.message}, error.timeout)
		return True
