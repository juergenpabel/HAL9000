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


	def __init__(self, action_name: str, plugin_cortex, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'kalliope', action_name, plugin_cortex, **kwargs)
		self.daemon.cortex['plugin']['kalliope'].state = Action.KALLIOPE_STATE_UNKNOWN
		self.daemon.cortex['plugin']['kalliope'].addNames(['audio_in', 'audio_out'])
		self.daemon.cortex['plugin']['kalliope'].addNameCallback(self.on_kalliope_state_callback, 'state')
		self.daemon.cortex['plugin']['kalliope'].addNameCallback(self.on_kalliope_volume_callback, 'volume')
		self.daemon.cortex['plugin']['kalliope'].addNameCallback(self.on_kalliope_mute_callback, 'mute')
		self.daemon.cortex['plugin']['kalliope'].addSignalHandler(self.on_kalliope_signal)
		self.daemon.cortex['plugin']['brain'].addNameCallback(self.on_brain_state_callback, 'state')


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


	async def on_kalliope_signal(self, plugin, signal):
		if 'state' in signal:
			match signal['state']:
				case Action.KALLIOPE_STATE_STARTING:
					if self.daemon.cortex['plugin']['kalliope'].state == Action.KALLIOPE_STATE_UNKNOWN:
						self.daemon.cortex['plugin']['kalliope'].state = signal['state']
				case Action.KALLIOPE_STATE_READY:
					if self.daemon.cortex['plugin']['kalliope'].state == Action.KALLIOPE_STATE_STARTING:
						self.daemon.cortex['plugin']['kalliope'].state = signal['state']
				case Action.KALLIOPE_STATE_WAITING:
					if self.daemon.cortex['plugin']['brain'].state in [Action.KALLIOPE_STATE_STARTING, Daemon.BRAIN_STATE_AWAKE]:
						self.daemon.cortex['plugin']['kalliope'].state = signal['state']
				case Action.KALLIOPE_STATE_LISTENING:
					if self.daemon.cortex['plugin']['brain'].state == Daemon.BRAIN_STATE_AWAKE:
						self.daemon.cortex['plugin']['kalliope'].state = signal['state']
				case Action.KALLIOPE_STATE_THINKING:
					if self.daemon.cortex['plugin']['brain'].state == Daemon.BRAIN_STATE_AWAKE:
						self.daemon.cortex['plugin']['kalliope'].state = signal['state']
				case Action.KALLIOPE_STATE_SPEAKING:
					if self.daemon.cortex['plugin']['brain'].state == Daemon.BRAIN_STATE_AWAKE:
						self.daemon.cortex['plugin']['kalliope'].state = signal['state']
				case Action.KALLIOPE_STATE_SLEEPING:
					if self.daemon.cortex['plugin']['kalliope'].state in [Action.KALLIOPE_STATE_WAITING, Action.KALLIOPE_STATE_LISTENING, \
							                                      Action.KALLIOPE_STATE_THINKING, Action.KALLIOPE_STATE_SPEAKING]:
						self.daemon.cortex['plugin']['kalliope'].state = signal['state']


	def on_kalliope_state_callback(self, plugin, key, old_state, new_state) -> bool:
		if old_state in [Action.KALLIOPE_STATE_UNKNOWN, Action.KALLIOPE_STATE_STARTING]:
			if new_state in [Action.KALLIOPE_STATE_STARTING, Action.KALLIOPE_STATE_READY]:
				return True
		match new_state:
			case Action.KALLIOPE_STATE_READY:
				self.daemon.cortex['plugin']['kalliope'].audio_in = 'none'
				self.daemon.cortex['plugin']['kalliope'].audio_out = 'none'
			case  Action.KALLIOPE_STATE_WAITING:
				self.daemon.cortex['plugin']['kalliope'].audio_in = 'wake-word-detector'
				self.daemon.cortex['plugin']['kalliope'].audio_out = 'none'
				if old_state == Action.KALLIOPE_STATE_SLEEPING:
					if self.config['kalliope:trigger-mqtt-topic'] is not None:
						self.daemon.mqtt_publish_queue.put_nowait({'topic': self.config['kalliope:trigger-mqtt-topic'], 'payload': 'unpause'})
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
				if self.config['kalliope:trigger-mqtt-topic'] is not None:
					self.daemon.mqtt_publish_queue.put_nowait( {'topic': self.config['kalliope:trigger-mqtt-topic'], 'payload': 'pause'})
			case _:
				return False
		return True


	def on_kalliope_volume_callback(self, plugin, key, old_volume, new_volume) -> bool:
		if plugin.mute in ['false', HAL9000_Plugin_Cortex.UNINITIALIZED]:
			self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': new_volume}})
		return True


	def on_kalliope_mute_callback(self, plugin, key, old_mute, new_mute) -> bool:
		match new_mute:
			case True:
				self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': 0}})
			case False:
				self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': plugin.volume}})
		return True


	def on_brain_state_callback(self, plugin, key, old_state, new_state) -> bool:
		if self.daemon.cortex['plugin']['kalliope'].state in [Action.KALLIOPE_STATE_READY, Action.KALLIOPE_STATE_WAITING]:
			if new_state == Daemon.BRAIN_STATE_READY:
				self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/welcome', 'payload': ''})
				return True
		match new_state:
			case Daemon.BRAIN_STATE_AWAKE:
				if self.daemon.cortex['plugin']['kalliope'].state == Action.KALLIOPE_STATE_SLEEPING:
					self.daemon.cortex['plugin']['kalliope'].state = Action.KALLIOPE_STATE_WAITING
			case Daemon.BRAIN_STATE_ASLEEP:
				self.daemon.cortex['plugin']['kalliope'].state = Action.KALLIOPE_STATE_SLEEPING
		return True

