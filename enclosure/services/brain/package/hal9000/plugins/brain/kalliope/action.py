#!/usr/bin/python3

import os
import json
import configparser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain.modules import HAL9000_Action
from hal9000.brain.daemon import Daemon


class Action(HAL9000_Action):

	KALLIOPE_STATE_UNKNOWN   = 'unknown'
	KALLIOPE_STATE_STARTING  = 'starting'
	KALLIOPE_STATE_READY     = 'ready'
	KALLIOPE_STATE_WAITING   = 'waiting'
	KALLIOPE_STATE_LISTENING = 'listening'
	KALLIOPE_STATE_THINKING  = 'thinking'
	KALLIOPE_STATE_SPEAKING  = 'speaking'
	KALLIOPE_STATES_RUNNING = [KALLIOPE_STATE_WAITING, KALLIOPE_STATE_LISTENING, KALLIOPE_STATE_THINKING, KALLIOPE_STATE_SPEAKING]


	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'kalliope', action_name, **kwargs)


	def configure(self, configuration: configparser.ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		self.config['kalliope-status-mqtt-topic'] = configuration.get(section_name, 'kalliope-status-mqtt-topic', fallback='hal9000/command/kalliope/status')
		self.config['kalliope-trigger-mqtt-topic'] = configuration.get(section_name, 'kalliope-trigger-mqtt-topic', fallback=None)
		cortex['kalliope'] = dict()
		cortex['kalliope']['state'] = Action.KALLIOPE_STATE_UNKNOWN


	def runlevel(self, cortex: dict) -> str:
		if cortex['kalliope']['state'] in [Action.KALLIOPE_STATE_UNKNOWN, Action.KALLIOPE_STATE_STARTING]:
			return cortex['kalliope']['state']
		return Action.MODULE_RUNLEVEL_RUNNING


	def runlevel_error(self, cortex: dict) -> dict:
		return {'code': 'TODO',
		        'level': 'error',
		        'message': "No connection to kalliope. Voice commands will not work.",
		        'audio': None}


	def process(self, signal: dict, cortex: dict) -> None:
		if 'brain' in signal:
			if 'status' in signal['brain']:
				mqtt_publish_message(self.config['kalliope-status-mqtt-topic'], json.dumps(signal['brain']['status']), hostname=os.getenv('MQTT_SERVER', default='127.0.0.1'), port=int(os.getenv('MQTT_PORT', default='1883')), client_id='brain')
			if 'consciousness' in signal['brain']:
				brain_state = signal['brain']['consciousness']
				if brain_state == Daemon.CONSCIOUSNESS_AWAKE:
					if self.config['kalliope-trigger-mqtt-topic'] is not None:
						mqtt_publish_message(self.config['kalliope-trigger-mqtt-topic'], 'unpause', hostname=os.getenv('MQTT_SERVER', default='127.0.0.1'), port=int(os.getenv('MQTT_PORT', default='1883')), client_id='brain')
				if brain_state == Daemon.CONSCIOUSNESS_ASLEEP:
					if self.config['kalliope-trigger-mqtt-topic'] is not None:
						mqtt_publish_message(self.config['kalliope-trigger-mqtt-topic'], 'pause', hostname=os.getenv('MQTT_SERVER', default='127.0.0.1'), port=int(os.getenv('MQTT_PORT', default='1883')), client_id='brain')
		if 'kalliope' in signal:
			if 'state' in signal['kalliope']:
				kalliope_state = signal['kalliope']['state']
				if cortex['kalliope']['state'] in [Action.KALLIOPE_STATE_UNKNOWN, Action.KALLIOPE_STATE_STARTING]:
					if kalliope_state in [Action.KALLIOPE_STATE_STARTING, Action.KALLIOPE_STATE_READY]:
						cortex['kalliope']['state'] = kalliope_state
				if kalliope_state in Action.KALLIOPE_STATES_RUNNING:
					cortex['kalliope']['state'] = kalliope_state
					if cortex['#consciousness'] == Daemon.CONSCIOUSNESS_AWAKE:
						if kalliope_state == Action.KALLIOPE_STATE_LISTENING:
							self.daemon.video_gui_screen_show('hal9000', {'queue': 'replace', 'sequence': {'name': 'wakeup', 'loop': 'false'}})
							self.daemon.video_gui_screen_show('hal9000', {'queue': 'append',  'sequence': {'name': 'active', 'loop': 'true'}})
						if kalliope_state == Action.KALLIOPE_STATE_WAITING:
							self.daemon.video_gui_screen_show('hal9000', {'queue': 'replace', 'sequence': {'name': 'sleep',  'loop': 'false'}})
							self.daemon.cortex['#activity']['video'].screen = 'idle'
					if cortex['#consciousness'] == Daemon.CONSCIOUSNESS_ASLEEP:
						if self.config['kalliope-trigger-mqtt-topic'] is not None:
							mqtt_publish_message(self.config['kalliope-trigger-mqtt-topic'], 'pause', hostname=os.getenv('MQTT_SERVER', default='127.0.0.1'), port=int(os.getenv('MQTT_PORT', default='1883')), client_id='brain')

