import os
import json
import configparser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin_Cortex
from hal9000.brain.daemon import Daemon


class Action(HAL9000_Action):

	KALLIOPE_STATE_UNKNOWN   = 'unknown'
	KALLIOPE_STATE_STARTING  = 'starting'
	KALLIOPE_STATE_READY     = 'ready'
	KALLIOPE_STATE_SLEEPING  = 'sleeping'
	KALLIOPE_STATE_WAITING   = 'waiting'
	KALLIOPE_STATE_LISTENING = 'listening'
	KALLIOPE_STATE_THINKING  = 'thinking'
	KALLIOPE_STATE_SPEAKING  = 'speaking'
	KALLIOPE_STATES_RUNNING = [KALLIOPE_STATE_SLEEPING, KALLIOPE_STATE_WAITING, KALLIOPE_STATE_LISTENING, KALLIOPE_STATE_THINKING, KALLIOPE_STATE_SPEAKING]


	def __init__(self, action_name: str, plugin_cortex, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'kalliope', action_name, plugin_cortex, **kwargs)
		self.daemon.cortex['plugin']['kalliope'].state = Action.KALLIOPE_STATE_UNKNOWN
		self.daemon.cortex['plugin']['kalliope'].addNames(['audio_in', 'audio_out'])
		self.daemon.cortex['plugin']['kalliope'].addNameCallback(self.on_kalliope_state_callback, 'state')
		self.daemon.cortex['plugin']['kalliope'].addNameCallback(self.on_kalliope_volume_callback, 'volume')
		self.daemon.cortex['plugin']['kalliope'].addNameCallback(self.on_kalliope_mute_callback, 'mute')
		self.daemon.cortex['plugin']['kalliope'].addSignalHandler(self.on_kalliope_signal)
		self.daemon.cortex['plugin']['brain'].addNameCallback(self.on_brain_state_callback, 'state')
		self.daemon.cortex['plugin']['brain'].addNameCallback(self.on_brain_consciousness_callback, 'consciousness')


	def configure(self, configuration: configparser.ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['kalliope:status-mqtt-topic'] = configuration.get(section_name, 'kalliope-status-mqtt-topic', fallback='hal9000/command/kalliope/status')
		self.config['kalliope:trigger-mqtt-topic'] = configuration.get(section_name, 'kalliope-trigger-mqtt-topic', fallback=None)


	def runlevel(self) -> str:
		if self.daemon.cortex['plugin']['kalliope'].state in [Action.KALLIOPE_STATE_UNKNOWN, Action.KALLIOPE_STATE_STARTING]:
			return self.daemon.cortex['plugin']['kalliope'].state
		return Action.PLUGIN_RUNLEVEL_RUNNING


	def runlevel_error(self) -> dict:
		return {'code': '02',
		        'level': 'error',
		        'message': "No connection to kalliope."}


	def on_kalliope_signal(self, plugin, signal):
		if 'state' in signal:
			if self.daemon.cortex['plugin']['brain'].consciousness == Daemon.CONSCIOUSNESS_AWAKE:
				self.daemon.cortex['plugin']['kalliope'].state = signal['state']
			if self.daemon.cortex['plugin']['brain'].consciousness == Daemon.CONSCIOUSNESS_ASLEEP:
				if self.config['kalliope:trigger-mqtt-topic'] is not None:
					self.daemon.mqtt.publish(self.config['kalliope:trigger-mqtt-topic'], 'pause')
				self.daemon.cortex['plugin']['kalliope'].state = Action.KALLIOPE_STATE_SLEEPING


	def on_kalliope_state_callback(self, plugin, key, old_value, new_value) -> bool:
		if old_value in [Action.KALLIOPE_STATE_UNKNOWN, Action.KALLIOPE_STATE_STARTING]:
			if new_value not in [Action.KALLIOPE_STATE_STARTING, Action.KALLIOPE_STATE_READY, Action.KALLIOPE_STATE_SLEEPING]:
				return False
		match new_value:
			case Action.KALLIOPE_STATE_READY:
				self.daemon.cortex['plugin']['kalliope'].audio_in = 'none'
				self.daemon.cortex['plugin']['kalliope'].audio_out = 'none'
			case  Action.KALLIOPE_STATE_WAITING:
				self.daemon.cortex['plugin']['kalliope'].audio_in = 'wake-word-detector'
				self.daemon.cortex['plugin']['kalliope'].audio_out = 'none'
			case Action.KALLIOPE_STATE_LISTENING:
				self.daemon.cortex['plugin']['kalliope'].audio_in = 'speech-to-text'
				self.daemon.cortex['plugin']['kalliope'].audio_out = 'none'
			case Action.KALLIOPE_STATE_THINKING:
				self.daemon.cortex['plugin']['kalliope'].audio_in = 'none'
				self.daemon.cortex['plugin']['kalliope'].audio_out = 'none'
			case Action.KALLIOPE_STATE_SPEAKING:
				self.daemon.cortex['plugin']['kalliope'].audio_in = 'none'
				self.daemon.cortex['plugin']['kalliope'].audio_out = 'text-to-speech'
			case Action.KALLIOPE_STATE_SLEEPING:
				self.daemon.cortex['plugin']['kalliope'].audio_in = 'none'
				self.daemon.cortex['plugin']['kalliope'].audio_out = 'none'
		return True


	def on_kalliope_volume_callback(self, plugin, key, old_value, new_value) -> bool:
		if plugin.mute in ['false', HAL9000_Plugin_Cortex.UNINITIALIZED]:
			self.daemon.cortex['plugin']['mqtt'].signal({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': new_value}})
		return True


	def on_kalliope_mute_callback(self, plugin, key, old_value, new_value) -> bool:
		match new_value:
			case True:
				self.daemon.cortex['plugin']['mqtt'].signal({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': 0}})
			case False:
				self.daemon.cortex['plugin']['mqtt'].signal({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': plugin.volume}})
		return True


	def on_brain_state_callback(self, plugin, key, old_value, new_value) -> bool:
		if new_value == 'ready':
			self.daemon.mqtt.publish('hal9000/command/kalliope/welcome', '')
		return True


	def on_brain_consciousness_callback(self, plugin, key, old_value, new_value) -> bool:
		if self.daemon.cortex['plugin']['kalliope'].state in Action.KALLIOPE_STATES_RUNNING:
			match new_value:
				case Daemon.CONSCIOUSNESS_AWAKE:
					if self.config['kalliope:trigger-mqtt-topic'] is not None:
						self.daemon.mqtt.publish(self.config['kalliope:trigger-mqtt-topic'], 'unpause')
					self.daemon.cortex['plugin']['kalliope'].state = Action.KALLIOPE_STATE_WAITING
				case Daemon.CONSCIOUSNESS_ASLEEP:
					if self.config['kalliope:trigger-mqtt-topic'] is not None:
						self.daemon.mqtt.publish(self.config['kalliope:trigger-mqtt-topic'], 'pause')
					self.daemon.cortex['plugin']['kalliope'].state = Action.KALLIOPE_STATE_SLEEPING
		return True

