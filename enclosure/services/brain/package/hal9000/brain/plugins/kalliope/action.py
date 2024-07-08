import os
import json
import configparser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin_Status
from hal9000.brain.daemon import Daemon


class Action(HAL9000_Action):

	KALLIOPE_STATUS_UNKNOWN   = 'unknown'
	KALLIOPE_STATUS_STARTING  = 'starting'
	KALLIOPE_STATUS_READY     = 'ready'
	KALLIOPE_STATUS_SLEEPING  = 'sleeping'
	KALLIOPE_STATUS_WAITING   = 'waiting'
	KALLIOPE_STATUS_LISTENING = 'listening'
	KALLIOPE_STATUS_THINKING  = 'thinking'
	KALLIOPE_STATUS_SPEAKING  = 'speaking'


	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Status, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'kalliope', action_name, plugin_status, **kwargs)
		self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_UNKNOWN
		self.daemon.plugins['kalliope'].addNames(['audio_in', 'audio_out'])
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_volume_callback, 'volume')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_mute_callback, 'mute')
		self.daemon.plugins['kalliope'].addSignalHandler(self.on_kalliope_signal)
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')


	def configure(self, configuration: configparser.ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['kalliope:status-mqtt-topic'] = configuration.get(section_name, 'kalliope-status-mqtt-topic', fallback='hal9000/command/kalliope/status')
		self.config['kalliope:trigger-mqtt-topic'] = configuration.get(section_name, 'kalliope-trigger-mqtt-topic', fallback=None)


	def runlevel(self) -> str:
		if self.daemon.plugins['kalliope'].status in [Action.KALLIOPE_STATUS_UNKNOWN, Action.KALLIOPE_STATUS_STARTING]:
			return self.daemon.plugins['kalliope'].status
		return Action.PLUGIN_RUNLEVEL_RUNNING


	def runlevel_error(self) -> dict:
		return {'code': '02',
		        'level': 'error',
		        'message': "No connection to kalliope."}


	async def on_kalliope_signal(self, plugin: HAL9000_Plugin_Status, signal: dict) -> None:
		if 'status' in signal:
			match signal['status']:
				case Action.KALLIOPE_STATUS_STARTING:
					if self.daemon.plugins['kalliope'].status == Action.KALLIOPE_STATUS_UNKNOWN:
						self.daemon.plugins['kalliope'].status = signal['status']
				case Action.KALLIOPE_STATUS_READY:
					if self.daemon.plugins['kalliope'].status in [Action.KALLIOPE_STATUS_UNKNOWN, Action.KALLIOPE_STATUS_STARTING]:
						self.daemon.plugins['kalliope'].status = signal['status']
				case Action.KALLIOPE_STATUS_WAITING:
					if self.daemon.plugins['brain'].status in [Daemon.BRAIN_STATUS_STARTING, Daemon.BRAIN_STATUS_AWAKE]:
						self.daemon.plugins['kalliope'].status = signal['status']
				case Action.KALLIOPE_STATUS_LISTENING:
					if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = signal['status']
				case Action.KALLIOPE_STATUS_THINKING:
					if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = signal['status']
				case Action.KALLIOPE_STATUS_SPEAKING:
					if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = signal['status']
				case Action.KALLIOPE_STATUS_SLEEPING:
					if self.daemon.plugins['kalliope'].status in [Action.KALLIOPE_STATUS_WAITING, Action.KALLIOPE_STATUS_LISTENING, \
							                                      Action.KALLIOPE_STATUS_THINKING, Action.KALLIOPE_STATUS_SPEAKING]:
						self.daemon.plugins['kalliope'].status = signal['status']


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_status: str, new_status: str) -> bool:
		match new_status:
			case Action.KALLIOPE_STATUS_READY:
				self.daemon.plugins['kalliope'].audio_in = 'none'
				self.daemon.plugins['kalliope'].audio_out = 'none'
			case  Action.KALLIOPE_STATUS_WAITING:
				self.daemon.plugins['kalliope'].audio_in = 'wake-word-detector'
				self.daemon.plugins['kalliope'].audio_out = 'none'
				if old_status == Action.KALLIOPE_STATUS_SLEEPING:
					if self.config['kalliope:trigger-mqtt-topic'] is not None:
						self.daemon.mqtt_publish_queue.put_nowait({'topic': self.config['kalliope:trigger-mqtt-topic'], 'payload': 'unpause'})
			case Action.KALLIOPE_STATUS_LISTENING:
				self.daemon.plugins['kalliope'].audio_in = 'speech-to-text'
				self.daemon.plugins['kalliope'].audio_out = 'none'
			case Action.KALLIOPE_STATUS_THINKING:
				self.daemon.plugins['kalliope'].audio_in = 'none'
				self.daemon.plugins['kalliope'].audio_out = 'none'
			case Action.KALLIOPE_STATUS_SPEAKING:
				self.daemon.plugins['kalliope'].audio_in = 'none'
				self.daemon.plugins['kalliope'].audio_out = 'text-to-speech'
			case Action.KALLIOPE_STATUS_SLEEPING:
				self.daemon.plugins['kalliope'].audio_in = 'none'
				self.daemon.plugins['kalliope'].audio_out = 'none'
				if self.config['kalliope:trigger-mqtt-topic'] is not None:
					self.daemon.mqtt_publish_queue.put_nowait( {'topic': self.config['kalliope:trigger-mqtt-topic'], 'payload': 'pause'})
			case other:
				return False
		return True


	def on_kalliope_volume_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_volume: int, new_volume: int) -> bool:
		if plugin.mute in ['false', HAL9000_Plugin_Status.UNINITIALIZED]:
			self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': new_volume}})
		return True


	def on_kalliope_mute_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_mute: str, new_mute: str) -> bool:
		match new_mute:
			case 'true':
				self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': 0}})
			case 'false':
				self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': plugin.volume}})
			case other:
				self.daemon.logger.error(f"[kalliope] invalid value '{new_mute}' for mute, ignoring")
				return False
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_status: str, new_status: str) -> bool:
		if self.daemon.plugins['kalliope'].status in [Action.KALLIOPE_STATUS_READY, Action.KALLIOPE_STATUS_WAITING]:
			if old_status == Daemon.BRAIN_STATUS_READY and new_status == Daemon.BRAIN_STATUS_AWAKE:
				self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/welcome', 'payload': ''})
				return True
		match new_status:
			case Daemon.BRAIN_STATUS_AWAKE:
				if self.daemon.plugins['kalliope'].status == Action.KALLIOPE_STATUS_SLEEPING:
					self.daemon.queue_signal('kalliope', {'status': Action.KALLIOPE_STATUS_WAITING})
			case Daemon.BRAIN_STATUS_ASLEEP:
				if self.daemon.plugins['kalliope'].status != Action.KALLIOPE_STATUS_SLEEPING:
					self.daemon.queue_signal('kalliope', {'status': Action.KALLIOPE_STATUS_SLEEPING})
		return True

