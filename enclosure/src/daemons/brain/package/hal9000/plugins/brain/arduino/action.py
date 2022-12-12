#!/usr/bin/python3

from configparser import ConfigParser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain.modules import HAL9000_Action
from hal9000.brain.daemon import Daemon


class Action(HAL9000_Action):

	WEBSERIAL_STATE_UNKNOWN = 'unknown'
	WEBSERIAL_STATE_OFFLINE = 'offline'
	WEBSERIAL_STATE_ONLINE  = 'online'
	WEBSERIAL_STATES_VALID = [WEBSERIAL_STATE_OFFLINE, WEBSERIAL_STATE_ONLINE]


	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'arduino', action_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		cortex['arduino'] = dict()
		cortex['arduino']['webserial'] = Action.WEBSERIAL_STATE_UNKNOWN


	def runlevel(self, cortex: dict) -> str:
		if cortex['arduino']['webserial'] == Action.WEBSERIAL_STATE_ONLINE:
			return Action.MODULE_RUNLEVEL_RUNNING
		return Action.MODULE_RUNLEVEL_BOOTING


	def runlevel_error(self, cortex: dict) -> dict:
		return {"code": "001",
		        "level": "error",
		        "message": "No connection to microcontroller. Display and inputs/sensors will not work.",
		        "audio": "error/001-arduino.wav",
		        "image": None}


	def process(self, signal: dict, cortex: dict) -> None:
		if 'arduino' in signal:
			if 'webserial' in signal['arduino']:
				webserial_state = signal['arduino']['webserial']
				if webserial_state in Action.WEBSERIAL_STATES_VALID:
					cortex['arduino']['webserial'] = webserial_state
				if webserial_state == Action.WEBSERIAL_STATE_ONLINE:
					self.daemon.arduino_set_system_time()

