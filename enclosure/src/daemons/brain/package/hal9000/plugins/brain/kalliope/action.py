#!/usr/bin/python3

from configparser import ConfigParser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain import HAL9000_Action
from hal9000.brain.daemon import Daemon


class Action(HAL9000_Action):

	KALLIOPE_STATE_STARTED   = 'started'
	KALLIOPE_STATE_WAITING   = 'waiting'
	KALLIOPE_STATE_LISTENING = 'listening'
	KALLIOPE_STATE_THINKING  = 'thinking'
	KALLIOPE_STATE_SPEAKING  = 'speaking'
	KALLIOPE_STATES_VALID = [KALLIOPE_STATE_STARTED, KALLIOPE_STATE_WAITING, KALLIOPE_STATE_LISTENING, KALLIOPE_STATE_THINKING, KALLIOPE_STATE_SPEAKING]


	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'kalliope', action_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		self.config['kalliope-trigger-mqtt-topic'] = configuration.get(section_name, 'kalliope-trigger-mqtt-topic', fallback=None)
		cortex['kalliope'] = dict()
		cortex['kalliope']['state'] = None


	def process(self, signal: dict, cortex: dict) -> None:
		if self.config['kalliope-trigger-mqtt-topic'] is not None:
			if 'brain' in signal:
				if 'consciousness' in signal['brain']:
					brain_state = signal['brain']['consciousness']
					if brain_state == Daemon.CONSCIOUSNESS_AWAKE:
						mqtt_publish_message(self.config['kalliope-trigger-mqtt-topic'], "unpause")
					if brain_state == Daemon.CONSCIOUSNESS_ASLEEP:
						mqtt_publish_message(self.config['kalliope-trigger-mqtt-topic'], "pause")
			if 'kalliope' in signal:
				if 'state' in signal['kalliope']:
					kalliope_state = signal['kalliope']['state']
					if kalliope_state in Action.KALLIOPE_STATES_VALID:
						cortex['kalliope']['state'] = kalliope_state
						if cortex['brain']['consciousness'] == Daemon.CONSCIOUSNESS_ASLEEP:
							mqtt_publish_message(self.config['kalliope-trigger-mqtt-topic'], "pause")

