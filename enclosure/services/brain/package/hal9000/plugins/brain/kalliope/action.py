#!/usr/bin/python3

import os
import json
import configparser

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
		self.config['kalliope:status-mqtt-topic'] = configuration.get(section_name, 'kalliope-status-mqtt-topic', fallback='hal9000/command/kalliope/status')
		self.config['kalliope:trigger-mqtt-topic'] = configuration.get(section_name, 'kalliope-trigger-mqtt-topic', fallback=None)
		cortex['service']['kalliope'].state = Action.KALLIOPE_STATE_UNKNOWN


	def runlevel(self, cortex: dict) -> str:
		if cortex['service']['kalliope'].state in [Action.KALLIOPE_STATE_UNKNOWN, Action.KALLIOPE_STATE_STARTING]:
			return cortex['service']['kalliope'].state
		return Action.MODULE_RUNLEVEL_RUNNING


	def runlevel_error(self, cortex: dict) -> dict:
		return {'code': '02',
		        'level': 'error',
		        'message': "No connection to kalliope."}


	def process(self, signal: dict, cortex: dict) -> None:
		if 'brain' in signal:
			if 'ready' in signal['brain']:
				self.daemon.mqtt.publish('hal9000/command/kalliope/ready', '')
			if 'status' in signal['brain']:
				self.daemon.mqtt.publish(self.config['kalliope:status-mqtt-topic'], json.dumps(signal['brain']['status']))
			if 'consciousness' in signal['brain']:
				brain_state = signal['brain']['consciousness']
				if brain_state == Daemon.CONSCIOUSNESS_AWAKE:
					if self.config['kalliope:trigger-mqtt-topic'] is not None:
						self.daemon.mqtt.publish(self.config['kalliope:trigger-mqtt-topic'], 'unpause')
				if brain_state == Daemon.CONSCIOUSNESS_ASLEEP:
					if self.config['kalliope:trigger-mqtt-topic'] is not None:
						self.daemon.mqtt.publish(self.config['kalliope:trigger-mqtt-topic'], 'pause')
		if 'kalliope' in signal:
			if 'state' in signal['kalliope']:
				kalliope_state = signal['kalliope']['state']
				if cortex['service']['kalliope'].state in [Action.KALLIOPE_STATE_UNKNOWN, Action.KALLIOPE_STATE_STARTING]:
					if kalliope_state in [Action.KALLIOPE_STATE_STARTING, Action.KALLIOPE_STATE_READY]:
						cortex['service']['kalliope'].state = kalliope_state
				if kalliope_state in Action.KALLIOPE_STATES_RUNNING:
					cortex['service']['kalliope'].state = kalliope_state
					if cortex['service']['brain'].consciousness == Daemon.CONSCIOUSNESS_AWAKE:
						if kalliope_state == Action.KALLIOPE_STATE_WAITING:
							self.daemon.video_gui_screen_show('hal9000', {'queue': 'replace', 'sequence': {'name': 'sleep',  'loop': 'false'}}, 3)
#TODO							self.daemon.cortex['service']['frontend'].screen = 'idle'
							self.daemon.cortex['service']['kalliope'].input = 'wake-word-detector'
							self.daemon.cortex['service']['kalliope'].output = 'none'
						if kalliope_state == Action.KALLIOPE_STATE_LISTENING:
							self.daemon.video_gui_screen_show('hal9000', {'queue': 'replace', 'sequence': {'name': 'wakeup', 'loop': 'false'}})
							self.daemon.video_gui_screen_show('hal9000', {'queue': 'append',  'sequence': {'name': 'active', 'loop': 'true'}})
							self.daemon.cortex['service']['kalliope'].input = 'speech-to-text'
							self.daemon.cortex['service']['kalliope'].output = 'none'
						if kalliope_state == Action.KALLIOPE_STATE_THINKING:
							self.daemon.cortex['service']['kalliope'].input = 'none'
							self.daemon.cortex['service']['kalliope'].output = 'none'
						if kalliope_state == Action.KALLIOPE_STATE_SPEAKING:
							self.daemon.cortex['service']['kalliope'].input = 'none'
							self.daemon.cortex['service']['kalliope'].output = 'text-to-speech'
					if cortex['service']['brain'].consciousness == Daemon.CONSCIOUSNESS_ASLEEP:
						if self.config['kalliope:trigger-mqtt-topic'] is not None:
							self.daemon.mqtt.publish(self.config['kalliope:trigger-mqtt-topic'], 'pause')

