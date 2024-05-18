#!/usr/bin/python3

import os
import json
import configparser
from datetime import datetime
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain.modules import HAL9000_Action
from hal9000.brain.daemon import Daemon


class Action(HAL9000_Action):

	FRONTEND_STATE_UNKNOWN = 'unknown'
	FRONTEND_STATE_OFFLINE = 'offline'
	FRONTEND_STATE_ONLINE  = 'online'
	FRONTEND_STATES_VALID = [FRONTEND_STATE_OFFLINE, FRONTEND_STATE_ONLINE]


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
		if cortex['frontend']['state'] == Action.FRONTEND_STATE_ONLINE:
			return Action.MODULE_RUNLEVEL_RUNNING
		return Action.MODULE_RUNLEVEL_STARTING


	def runlevel_error(self, cortex: dict) -> dict:
		return {"code": "020",
		        "level": "fatal",
		        "message": "No connection to microcontroller. Display and inputs/sensors will not work.",
		        "audio": "error/001-frontend.wav"}


	def process(self, signal: dict, cortex: dict) -> None:
		if 'brain' in signal:
			if 'status' in signal['brain']:
				mqtt_publish_message(self.config['frontend-status-mqtt-topic'], json.dumps(signal['brain']['status']), hostname=os.getenv('MQTT_SERVER', default='127.0.0.1'), port=int(os.getenv('MQTT_PORT', default='1883')))
			if 'consciousness' in signal['brain']:
				self.send_command("application/runtime", json.dumps({"condition": signal['brain']['consciousness']}))
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
					cortex['#activity']['video'].screen = signal['frontend']['gui']['screen']
				if 'overlay' in signal['frontend']['gui']:
					cortex['#activity']['video'].overlay = signal['frontend']['gui']['overlay']
			if 'error' in signal['frontend']:
				code = signal['frontend']['error']['code']
				message = signal['frontend']['error']['message']
				timeout = None
				if 'timeout' in signal['frontend']['error']:
					timeout = int(signal['frontend']['error']['timeout'])
				if cortex['#activity']['video'].screen == 'idle':
					self.daemon.video_gui_screen_show("error", {'code': code, 'message': message}, timeout)
				else:
					self.error_queue.append({'code': code, 'message': message, 'timeout': timeout})


	def send_command(self, topic, body) -> None:
		mqtt_publish_message(f"hal9000/command/frontend/{topic}", body, hostname=os.getenv('MQTT_SERVER', default='127.0.0.1'), port=int(os.getenv('MQTT_PORT', default='1883')))


	def send_system_time(self, synced: bool = False):
		body = {"time": {"epoch": int(datetime.now().timestamp() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds), "synced": synced}}
		self.send_command("application/runtime", json.dumps(body));


	def on_video_activity(self, target, item, old_value, new_value):
		if self.daemon.cortex['frontend']['state'] != Action.FRONTEND_STATE_ONLINE:
			return False
		if item == 'signal':
			if 'activity' in new_value:
				if 'gui' in new_value['activity']:
					if 'screen' in new_value['activity']['gui']:
						screen = new_value['activity']['gui']['screen']['name']
						parameter = new_value['activity']['gui']['screen']['parameter']
						self.send_command("gui/screen", json.dumps({screen: parameter}))
					if 'overlay' in new_value['activity']['gui']:
						overlay = new_value['activity']['gui']['overlay']['name']
						parameter = new_value['activity']['gui']['overlay']['parameter']
						self.send_command("gui/overlay", json.dumps({overlay: parameter}))
#TODO		if item == 'screen' and new_value == 'idle':
#TODO			if len(self.error_queue) > 0:
#TODO				error = error_queue.pop(0)
#TODO				self.daemon.video_gui_screen_show("error", {'code': error.code, 'message': error.message}, error.timeout)
		return True
