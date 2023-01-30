#!/usr/bin/python3

import json
from datetime import datetime
from configparser import ConfigParser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.daemon.arduino.modules import HAL9000_Action
from hal9000.daemon.arduino import Daemon


class Action(HAL9000_Action):

	WEBSERIAL_STATE_UNKNOWN = 'unknown'
	WEBSERIAL_STATE_OFFLINE = 'offline'
	WEBSERIAL_STATE_ONLINE  = 'online'
	WEBSERIAL_STATES_VALID = [WEBSERIAL_STATE_OFFLINE, WEBSERIAL_STATE_ONLINE]


	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'arduino', action_name, **kwargs)
		self.error_queue = list()
		self.daemon.cortex['#activity']['video'].addCallback(self.on_video_activity)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		cortex['arduino'] = dict()
		cortex['arduino']['webserial'] = Action.WEBSERIAL_STATE_UNKNOWN


	def runlevel(self, cortex: dict) -> str:
		if cortex['arduino']['webserial'] == Action.WEBSERIAL_STATE_ONLINE:
			return Action.MODULE_RUNLEVEL_RUNNING
		return Action.MODULE_RUNLEVEL_STARTING


	def runlevel_error(self, cortex: dict) -> dict:
		return {"code": "020",
		        "level": "fatal",
		        "message": "No connection to microcontroller. Display and inputs/sensors will not work.",
		        "audio": "error/001-arduino.wav"}


	def process(self, signal: dict, cortex: dict) -> None:
		if 'agent' in signal:
			if 'consciousness' in signal['agent']:
				self.send_command("application/runtime", json.dumps({"condition": signal['agent']['consciousness']}))
			if 'time' in signal['agent']:
				synced = False
				if 'synced' in signal['agent']['time']:
					synced = bool(signal['agent']['time']['synced'])
				self.send_system_time(synced)
		if 'arduino' in signal:
			if 'webserial' in signal['arduino']:
				webserial_state = signal['arduino']['webserial']
				if webserial_state in Action.WEBSERIAL_STATES_VALID:
					cortex['arduino']['webserial'] = webserial_state
					if webserial_state == 'online':
						self.send_system_time(False)
			if 'gui' in signal['arduino']:
				if 'screen' in signal['arduino']['gui']:
					cortex['#activity']['video'].screen = signal['arduino']['gui']['screen']
				if 'overlay' in signal['arduino']['gui']:
					cortex['#activity']['video'].overlay = signal['arduino']['gui']['overlay']
			if 'error' in signal['arduino']:
				code = signal['arduino']['error']['code']
				message = signal['arduino']['error']['message']
				timeout = None
				if 'timeout' in signal['arduino']['error']:
					timeout = int(signal['arduino']['error']['timeout'])
				if cortex['#activity']['video'].screen == 'idle':
					self.daemon.video_gui_screen_show("error", {'code': code, 'message': message}, timeout)
				else:
					self.error_queue.append({'code': code, 'message': message, 'timeout': timeout})


	def send_command(self, topic, body) -> None:
		mqtt_publish_message(f"hal9000/daemon/arduino-service/command:{topic}", body)


	def send_system_time(self, synced: bool = False):
		body = {"time": {"epoch": int(datetime.now().timestamp() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds), "synced": synced}}
		self.send_command("application/runtime", json.dumps(body));


	def on_video_activity(self, target, item, old_value, new_value):
		if self.daemon.cortex['arduino']['webserial'] != Action.WEBSERIAL_STATE_ONLINE:
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
