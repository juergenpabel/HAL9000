import os
import json
import configparser
from enum import StrEnum as enum_StrEnum

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data, DataInvalid, RUNLEVEL, CommitPhase
from hal9000.brain.daemon import BRAIN_STATUS


class KALLIOPE_STATUS(enum_StrEnum):
	WAITING   = 'waiting'
	LISTENING = 'listening'
	THINKING  = 'thinking'
	SPEAKING  = 'speaking'
	SLEEPING  = 'sleeping'


class Action(HAL9000_Action):

	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'kalliope', action_name, plugin_status, **kwargs)
		self.daemon.plugins['kalliope'].addLocalNames(['audio_in', 'audio_out', 'mute'])
		self.daemon.plugins['kalliope'].addRemoteNames(['volume'])
		self.daemon.plugins['kalliope'].runlevel = DataInvalid.UNKNOWN, CommitPhase.COMMIT


	def configure(self, configuration: configparser.ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['initial-volume'] = configuration.getint(section_name, 'initial-volume', fallback=50)
		self.config['trigger-mqtt-topic'] = configuration.get(section_name, 'trigger-mqtt-topic', fallback=None)
		self.config['command-mqtt-topic-prefix'] = configuration.get(section_name, 'command-mqtt-topic-prefix', fallback='hal9000/command/kalliope')
		self.daemon.add_runlevel_inhibitor(RUNLEVEL.READY, 'kalliope:volume',  self.runlevel_inhibitor_ready_volume)
		self.daemon.plugins['kalliope'].addSignalHandler(self.on_kalliope_signal)
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_volume_callback, 'volume')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_mute_callback, 'mute')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.mqtt_prefix = self.config['command-mqtt-topic-prefix']


	def runlevel_inhibitor_ready_volume(self) -> bool:
		if self.daemon.plugins['kalliope'].volume in list(DataInvalid):
			return False
		return True


	async def on_kalliope_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'runlevel' in signal:
			match signal['runlevel']:
				case RUNLEVEL.STARTING:
					if self.daemon.plugins['kalliope'].runlevel in [DataInvalid.UNKNOWN, RUNLEVEL.KILLED]:
						self.daemon.plugins['kalliope'].runlevel = RUNLEVEL.STARTING, CommitPhase.COMMIT
				case RUNLEVEL.READY:
					if self.daemon.plugins['kalliope'].runlevel in [DataInvalid.UNKNOWN, RUNLEVEL.STARTING]:
						self.daemon.plugins['kalliope'].runlevel = RUNLEVEL.READY
				case RUNLEVEL.RUNNING:
					if self.daemon.plugins['kalliope'].runlevel in [DataInvalid.UNKNOWN, RUNLEVEL.READY]:
						self.daemon.plugins['kalliope'].runlevel = RUNLEVEL.RUNNING
				case RUNLEVEL.KILLED:
					self.daemon.plugins['kalliope'].runlevel = RUNLEVEL.KILLED, CommitPhase.COMMIT
		if 'status' in signal:
			match signal['status']:
				case KALLIOPE_STATUS.WAITING:
					if self.daemon.plugins['brain'].status == BRAIN_STATUS.AWAKE:
						self.daemon.plugins['kalliope'].status = KALLIOPE_STATUS.WAITING
				case KALLIOPE_STATUS.LISTENING:
					if self.daemon.plugins['brain'].status == BRAIN_STATUS.AWAKE:
						self.daemon.plugins['kalliope'].status = KALLIOPE_STATUS.LISTENING
				case KALLIOPE_STATUS.THINKING:
					if self.daemon.plugins['brain'].status == BRAIN_STATUS.AWAKE:
						self.daemon.plugins['kalliope'].status = KALLIOPE_STATUS.THINKING
				case KALLIOPE_STATUS.SPEAKING:
					if self.daemon.plugins['brain'].status == BRAIN_STATUS.AWAKE:
						self.daemon.plugins['kalliope'].status = KALLIOPE_STATUS.SPEAKING
				case KALLIOPE_STATUS.SLEEPING:
					self.daemon.plugins['kalliope'].status = KALLIOPE_STATUS.SLEEPING
		if 'command' in signal:
			if 'name' in signal['command']:
				command_name = signal['command']['name']
				self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/{command_name}',
				                                  'payload': signal['command']['parameter'] if 'parameter' in signal['command'] else None})
		if 'volume' in signal:
			if 'level' in signal['volume']:
				if signal['volume']['level'] not in [DataInvalid.UNKNOWN, DataInvalid.UNINITIALIZED]:
					if int(signal['volume']['level']) >= 0 and int(signal['volume']['level']) <= 100:
						if 'origin' in signal['volume'] and signal['volume']['origin'].startswith('frontend') == True:
							if int(signal['volume']['level']) > 0 or self.daemon.plugins['kalliope'].mute == 'false':
								self.daemon.plugins['kalliope'].volume = str(signal['volume']['level']), CommitPhase.COMMIT
								self.daemon.plugins['kalliope'].mute = 'false', CommitPhase.COMMIT
						else:
							self.daemon.plugins['kalliope'].volume = str(signal['volume']['level'])
			if 'mute' in signal['volume']:
				self.daemon.plugins['kalliope'].mute = str(signal['volume']['mute']).lower(), CommitPhase.COMMIT
				match self.daemon.plugins['kalliope'].mute:
					case 'true':
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/volume', 'payload': {'level': 0}})
					case 'false':
						if self.daemon.plugins['kalliope'].volume not in[DataInvalid.UNINITIALIZED, DataInvalid.UNKNOWN]:
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/volume',
							                                  'payload': {'level': int(self.daemon.plugins['kalliope'].volume)}})


	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			match new_runlevel:
				case RUNLEVEL.STARTING:
					self.daemon.plugins['kalliope'].status = DataInvalid.UNKNOWN, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].audio_in = DataInvalid.UNKNOWN, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].audio_out = DataInvalid.UNKNOWN, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].volume = DataInvalid.UNKNOWN, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].mute = DataInvalid.UNKNOWN, CommitPhase.COMMIT
				case RUNLEVEL.READY:
					self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/status', 'payload': None})
					self.daemon.queue_signal('kalliope', {'volume': {'level': self.config['initial-volume'], 'mute': False}})
				case RUNLEVEL.KILLED:
					self.daemon.plugins['kalliope'].status = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].volume = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].mute = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].audio_in = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].audio_out = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.process_error('critical', '300', "System offline", f"Service 'kalliope' unavailable")
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_status not in list(KALLIOPE_STATUS):
					return False
			case CommitPhase.COMMIT:
				match new_status:
					case KALLIOPE_STATUS.SLEEPING:
						self.daemon.plugins['kalliope'].audio_in = 'none', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'none', CommitPhase.COMMIT
						if self.config['trigger-mqtt-topic'] is not None:
							self.daemon.queue_signal('mqtt', {'topic': self.config['trigger-mqtt-topic'], 'payload': 'pause'})
					case KALLIOPE_STATUS.WAITING:
						self.daemon.plugins['kalliope'].audio_in = 'wake-word-detector', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'none', CommitPhase.COMMIT
						if self.config['trigger-mqtt-topic'] is not None:
							self.daemon.queue_signal('mqtt', {'topic': self.config['trigger-mqtt-topic'], 'payload': 'unpause'})
					case KALLIOPE_STATUS.LISTENING:
						self.daemon.plugins['kalliope'].audio_in = 'speech-to-text', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'none', CommitPhase.COMMIT
					case KALLIOPE_STATUS.THINKING:
						self.daemon.plugins['kalliope'].audio_in = 'none', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'none', CommitPhase.COMMIT
					case KALLIOPE_STATUS.SPEAKING:
						self.daemon.plugins['kalliope'].audio_in = 'none', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'text-to-speech', CommitPhase.COMMIT
		return True


	def on_kalliope_volume_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_volume: str, new_volume: str, phase: CommitPhase) -> bool:
		if new_volume in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if self.daemon.plugins['kalliope'].mute == 'true':
					return False
				if int(new_volume) < 0 or int(new_volume) > 100:
					self.daemon.logger.info(f"[kalliope] ignoring volume change request due to invalid value '{new_volume}'")
					return False
			case CommitPhase.REMOTE_REQUESTED:
				self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/volume', 'payload': {'level': int(new_volume)}})
		return True


	def on_kalliope_mute_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_mute: str, new_mute: str, phase: CommitPhase) -> bool:
		if new_mute in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_mute not in ['true', 'false']:
					self.daemon.logger.info(f"[kalliope] inhibiting change of mute from '{old_mute}' to '{new_mute}'")
					return False
				match new_mute:
					case 'true':
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/volume', 'payload': {'level': 0}})
					case 'false':
						if self.daemon.plugins['kalliope'].volume not in [DataInvalid.UNKNOWN, DataInvalid.UNINITIALIZED]:
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/volume',
							                                  'payload': {'level': self.daemon.plugins['kalliope'].volume}})
		return True


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			match new_runlevel:
				case RUNLEVEL.READY:
					self.daemon.queue_signal('kalliope', {'volume': {'level': self.config['initial-volume'], 'mute': False}})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		if phase == CommitPhase.COMMIT:
			match new_status:
				case BRAIN_STATUS.AWAKE:
					self.daemon.queue_signal('kalliope', {'status': KALLIOPE_STATUS.WAITING})
				case BRAIN_STATUS.ASLEEP:
					self.daemon.queue_signal('kalliope', {'status': KALLIOPE_STATUS.SLEEPING})
		return True

