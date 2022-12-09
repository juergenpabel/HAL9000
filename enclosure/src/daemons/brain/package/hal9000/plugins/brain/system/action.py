#!/usr/bin/python3

from configparser import ConfigParser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain import HAL9000_Action
from hal9000.brain.daemon import Daemon


class Action(HAL9000_Action):

	SYSTEM_STATE_TIME_UNKNOWN   = 'unknown'
	SYSTEM_STATE_TIME_SYNCED   = 'synced'
	SYSTEM_STATES_VALID = [SYSTEM_STATE_TIME_UNKNOWN, SYSTEM_STATE_TIME_SYNCED]


	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'system', action_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		cortex['system'] = dict()
		cortex['system']['time'] = Action.SYSTEM_STATE_TIME_UNKNOWN


	def process(self, signal: dict, cortex: dict) -> None:
		if 'system' in signal:
			if 'time' in signal['system']:
				system_time_state = signal['system']['time']
				if system_time_state in Action.SYSTEM_STATES_VALID:
					cortex['system']['time'] = system_time_state
				if system_time_state == Action.SYSTEM_STATE_TIME_SYNCED:
					self.daemon.arduino_set_system_time()

