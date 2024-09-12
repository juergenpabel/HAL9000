import os
import json
import configparser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data
from hal9000.brain.daemon import Daemon


class Action(HAL9000_Action):

	KALLIOPE_STATUS_WAITING   = 'waiting'
	KALLIOPE_STATUS_LISTENING = 'listening'
	KALLIOPE_STATUS_THINKING  = 'thinking'
	KALLIOPE_STATUS_SPEAKING  = 'speaking'
	KALLIOPE_STATUS_SLEEPING  = 'sleeping'


	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'kalliope', action_name, plugin_status, **kwargs)
		self.daemon.plugins['kalliope'].runlevel = HAL9000_Action.RUNLEVEL_UNKNOWN
		self.daemon.plugins['kalliope'].addLocalNames(['audio_in', 'audio_out', 'volume', 'mute'])


	def configure(self, configuration: configparser.ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['kalliope:status-mqtt-topic'] = configuration.get(section_name, 'kalliope-status-mqtt-topic',
		                                                                 fallback='hal9000/command/kalliope/status')
		self.config['kalliope:trigger-mqtt-topic'] = configuration.get(section_name, 'kalliope-trigger-mqtt-topic', fallback=None)
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_volume_callback, 'volume')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_mute_callback, 'mute')
		self.daemon.plugins['kalliope'].addSignalHandler(self.on_kalliope_signal)
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')


	def runlevel(self) -> str:
		return self.daemon.plugins['kalliope'].runlevel


	def runlevel_error(self) -> dict:
		return {'id': '300',
		        'level': 'critical',
		        'title': "Service 'kalliope' unavailable (voice interaction)"}


	async def on_kalliope_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'runlevel' in signal:
			match signal['runlevel']:
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					if self.daemon.plugins['kalliope'].runlevel in [HAL9000_Plugin.RUNLEVEL_UNKNOWN, \
					                                                HAL9000_Plugin.RUNLEVEL_KILLED]:
						self.daemon.plugins['kalliope'].runlevel = HAL9000_Plugin.RUNLEVEL_STARTING
				case HAL9000_Plugin.RUNLEVEL_READY:
					if self.daemon.plugins['kalliope'].runlevel in [HAL9000_Plugin.RUNLEVEL_UNKNOWN, \
					                                                HAL9000_Plugin.RUNLEVEL_STARTING]:
						self.daemon.plugins['kalliope'].runlevel = HAL9000_Plugin.RUNLEVEL_READY
						self.daemon.plugins['kalliope'].audio_in = 'none'
						self.daemon.plugins['kalliope'].audio_out = 'none'
				case HAL9000_Plugin.RUNLEVEL_RUNNING:
					self.daemon.plugins['kalliope'].runlevel = HAL9000_Plugin.RUNLEVEL_RUNNING
					self.daemon.plugins['kalliope'].audio_in = 'none'
					self.daemon.plugins['kalliope'].audio_out = 'none'
					self.daemon.queue_signal('kalliope', {'status': Action.KALLIOPE_STATUS_WAITING})
				case HAL9000_Plugin.RUNLEVEL_KILLED:
					self.daemon.plugins['kalliope'].runlevel = HAL9000_Plugin.RUNLEVEL_KILLED
					self.daemon.plugins['kalliope'].status = HAL9000_Plugin_Data.STATUS_UNINITIALIZED
					self.daemon.plugins['kalliope'].volume = HAL9000_Plugin_Data.STATUS_UNINITIALIZED
					self.daemon.plugins['kalliope'].mute = HAL9000_Plugin_Data.STATUS_UNINITIALIZED
					self.daemon.plugins['kalliope'].audio_in = HAL9000_Plugin_Data.STATUS_UNINITIALIZED
					self.daemon.plugins['kalliope'].audio_out = HAL9000_Plugin_Data.STATUS_UNINITIALIZED
		if 'status' in signal:
			match signal['status']:
				case Action.KALLIOPE_STATUS_WAITING:
					if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_WAITING
				case Action.KALLIOPE_STATUS_LISTENING:
					if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_LISTENING
				case Action.KALLIOPE_STATUS_THINKING:
					if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_THINKING
				case Action.KALLIOPE_STATUS_SPEAKING:
					if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_SPEAKING
				case Action.KALLIOPE_STATUS_SLEEPING:
					self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_SLEEPING


	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, pending: bool) -> bool:
		if pending is False:
			match new_runlevel:
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					if old_runlevel == HAL9000_Plugin.RUNLEVEL_KILLED:
						self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
				case HAL9000_Plugin.RUNLEVEL_KILLED:
					self.daemon.process_error('critical', '300', "System offline", f"Service 'kalliope' unavailable")
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, pending: bool) -> bool:
		if pending is False:
			match new_status:
				case HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
					if self.daemon.plugins['kalliope'].runlevel != HAL9000_Plugin.RUNLEVEL_KILLED:
						return False
				case Action.KALLIOPE_STATUS_WAITING:
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


	def on_kalliope_volume_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_volume: int, new_volume: int, pending: bool) -> bool:
		if pending is False and new_volume != HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
			if plugin.mute in ['false', HAL9000_Plugin_Data.STATUS_UNINITIALIZED]:
				self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': new_volume}})
		return True


	def on_kalliope_mute_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_mute: str, new_mute: str, pending: bool) -> bool:
		if pending is False and new_mute != HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
			match new_mute:
				case 'true':
					self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': 0}})
				case 'false':
					if old_mute != HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
						self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/volume', 'payload': {'level': plugin.volume}})
				case other:
					self.daemon.logger.error(f"[kalliope] invalid value '{new_mute}' for mute, ignoring")
					return False
		return True


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, pending: bool) -> bool:
		if pending is False:
			if old_runlevel == HAL9000_Plugin.RUNLEVEL_READY and new_runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING:
				if self.daemon.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
					self.daemon.mqtt_publish_queue.put_nowait({'topic': 'hal9000/command/kalliope/welcome', 'payload': ''})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, pending: bool) -> bool:
		if pending is False:
			match new_status:
				case Daemon.BRAIN_STATUS_AWAKE:
					self.daemon.queue_signal('kalliope', {'status': Action.KALLIOPE_STATUS_WAITING})
				case Daemon.BRAIN_STATUS_ASLEEP:
					self.daemon.queue_signal('kalliope', {'status': Action.KALLIOPE_STATUS_SLEEPING})
		return True

