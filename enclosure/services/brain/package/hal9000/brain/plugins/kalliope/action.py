import os
import json
import configparser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Data, CommitPhase
from hal9000.brain.daemon import Brain


class Action(HAL9000_Action):

	KALLIOPE_STATUS_WAITING   = 'waiting'
	KALLIOPE_STATUS_LISTENING = 'listening'
	KALLIOPE_STATUS_THINKING  = 'thinking'
	KALLIOPE_STATUS_SPEAKING  = 'speaking'
	KALLIOPE_STATUS_SLEEPING  = 'sleeping'


	def __init__(self, action_name: str, plugin_status: HAL9000_Plugin_Data, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'kalliope', action_name, plugin_status, **kwargs)
		self.daemon.plugins['kalliope'].addLocalNames(['audio_in', 'audio_out', 'mute'])
		self.daemon.plugins['kalliope'].addRemoteNames(['volume'])
		self.daemon.plugins['kalliope'].runlevel = HAL9000_Action.RUNLEVEL_UNKNOWN, CommitPhase.COMMIT


	def configure(self, configuration: configparser.ConfigParser, section_name: str) -> None:
		HAL9000_Action.configure(self, configuration, section_name)
		self.config['initial-volume'] = configuration.getint(section_name, 'initial-volume', fallback=50)
		self.config['trigger-mqtt-topic'] = configuration.get(section_name, 'trigger-mqtt-topic', fallback=None)
		self.config['command-mqtt-topic-prefix'] = configuration.get(section_name, 'command-mqtt-topic-prefix', fallback='hal9000/command/kalliope')
		self.daemon.add_runlevel_inhibitor(HAL9000_Plugin.RUNLEVEL_READY, 'kalliope:status',  self.runlevel_inhibitor_ready_status)
		self.daemon.add_runlevel_inhibitor(HAL9000_Plugin.RUNLEVEL_READY, 'kalliope:volume',  self.runlevel_inhibitor_ready_volume)
		self.daemon.plugins['kalliope'].addSignalHandler(self.on_kalliope_signal)
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_volume_callback, 'volume')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_mute_callback, 'mute')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.mqtt_prefix = self.config['command-mqtt-topic-prefix']


	def runlevel(self) -> str:
		return self.daemon.plugins['kalliope'].runlevel


	def runlevel_error(self) -> dict:
		return {'id': '300',
		        'level': 'critical',
		        'title': "Service 'kalliope' unavailable (voice interaction)"}


	def runlevel_inhibitor_ready_status(self) -> bool:
		if self.daemon.plugins['kalliope'].status == 'unknown':
			return False
		return True


	def runlevel_inhibitor_ready_volume(self) -> bool:
		if self.daemon.plugins['kalliope'].volume == 'unknown':
			return False
		return True


	async def on_kalliope_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'runlevel' in signal:
			match signal['runlevel']:
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					if self.daemon.plugins['kalliope'].runlevel in [HAL9000_Plugin.RUNLEVEL_UNKNOWN, HAL9000_Plugin.RUNLEVEL_KILLED]:
						self.daemon.plugins['kalliope'].runlevel = HAL9000_Plugin.RUNLEVEL_STARTING, CommitPhase.COMMIT
				case HAL9000_Plugin.RUNLEVEL_READY:
					if self.daemon.plugins['kalliope'].runlevel in [HAL9000_Plugin.RUNLEVEL_UNKNOWN, HAL9000_Plugin.RUNLEVEL_STARTING]:
						self.daemon.plugins['kalliope'].runlevel = HAL9000_Plugin.RUNLEVEL_READY
				case HAL9000_Plugin.RUNLEVEL_RUNNING:
					if self.daemon.plugins['kalliope'].runlevel in [HAL9000_Plugin.RUNLEVEL_UNKNOWN, HAL9000_Plugin.RUNLEVEL_READY]:
						self.daemon.plugins['kalliope'].runlevel = HAL9000_Plugin.RUNLEVEL_RUNNING
				case HAL9000_Plugin.RUNLEVEL_KILLED:
					self.daemon.plugins['kalliope'].runlevel = HAL9000_Plugin.RUNLEVEL_KILLED, CommitPhase.COMMIT
		if 'status' in signal:
			match signal['status']:
				case Action.KALLIOPE_STATUS_WAITING:
					if self.daemon.plugins['brain'].status == Brain.STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_WAITING
				case Action.KALLIOPE_STATUS_LISTENING:
					if self.daemon.plugins['brain'].status == Brain.STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_LISTENING
				case Action.KALLIOPE_STATUS_THINKING:
					if self.daemon.plugins['brain'].status == Brain.STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_THINKING
				case Action.KALLIOPE_STATUS_SPEAKING:
					if self.daemon.plugins['brain'].status == Brain.STATUS_AWAKE:
						self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_SPEAKING
				case Action.KALLIOPE_STATUS_SLEEPING:
					self.daemon.plugins['kalliope'].status = Action.KALLIOPE_STATUS_SLEEPING
		if 'command' in signal:
			if 'name' in signal['command']:
				command_name = signal['command']['name']
				self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/{command_name}',
				                                  'payload': signal['command']['parameter'] if 'parameter' in signal['command'] else None})
		if 'volume' in signal:
			if 'level' in signal['volume']:
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
						if self.daemon.plugins['kalliope'].volume != HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
							self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/volume',
							                                  'payload': {'level': int(self.daemon.plugins['kalliope'].volume)}})


	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			match new_runlevel:
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					self.daemon.plugins['kalliope'].status = 'unknown', CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].audio_in = 'unknown', CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].audio_out = 'unknown', CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].volume = 'unknown', CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].mute = 'unknown', CommitPhase.COMMIT
				case HAL9000_Plugin.RUNLEVEL_READY:
					self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/status', 'payload': None})
				case HAL9000_Plugin.RUNLEVEL_KILLED:
					self.daemon.plugins['kalliope'].status = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].volume = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].mute = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].audio_in = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.plugins['kalliope'].audio_out = HAL9000_Plugin_Data.STATUS_UNINITIALIZED, CommitPhase.COMMIT
					self.daemon.process_error('critical', '300', "System offline", f"Service 'kalliope' unavailable")
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_status not in [Action.KALLIOPE_STATUS_SLEEPING, Action.KALLIOPE_STATUS_WAITING, Action.KALLIOPE_STATUS_LISTENING, \
				                      Action.KALLIOPE_STATUS_THINKING, Action.KALLIOPE_STATUS_SPEAKING]:
					return False
			case CommitPhase.COMMIT:
				match new_status:
					case Action.KALLIOPE_STATUS_SLEEPING:
						self.daemon.plugins['kalliope'].audio_in = 'none', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'none', CommitPhase.COMMIT
						if self.config['trigger-mqtt-topic'] is not None:
							self.daemon.queue_signal('mqtt', {'topic': self.config['trigger-mqtt-topic'], 'payload': 'pause'})
					case Action.KALLIOPE_STATUS_WAITING:
						self.daemon.plugins['kalliope'].audio_in = 'wake-word-detector', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'none', CommitPhase.COMMIT
						if self.config['trigger-mqtt-topic'] is not None:
							self.daemon.queue_signal('mqtt', {'topic': self.config['trigger-mqtt-topic'], 'payload': 'unpause'})
					case Action.KALLIOPE_STATUS_LISTENING:
						self.daemon.plugins['kalliope'].audio_in = 'speech-to-text', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'none', CommitPhase.COMMIT
					case Action.KALLIOPE_STATUS_THINKING:
						self.daemon.plugins['kalliope'].audio_in = 'none', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'none', CommitPhase.COMMIT
					case Action.KALLIOPE_STATUS_SPEAKING:
						self.daemon.plugins['kalliope'].audio_in = 'none', CommitPhase.COMMIT
						self.daemon.plugins['kalliope'].audio_out = 'text-to-speech', CommitPhase.COMMIT
		return True


	def on_kalliope_volume_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_volume: str, new_volume: str, phase: CommitPhase) -> bool:
		if new_volume == HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
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
		if new_mute == HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
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
						self.daemon.queue_signal('mqtt', {'topic': f'{self.mqtt_prefix}/volume', 'payload': {'level': plugin.volume}})
		return True


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			match new_runlevel:
				case HAL9000_Plugin.RUNLEVEL_READY:
					self.daemon.queue_signal('kalliope', {'volume': {'level': self.config['initial-volume'], 'mute': False}})


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			match new_status:
				case Brain.STATUS_AWAKE:
					self.daemon.queue_signal('kalliope', {'status': Action.KALLIOPE_STATUS_WAITING})
				case Brain.STATUS_ASLEEP:
					self.daemon.queue_signal('kalliope', {'status': Action.KALLIOPE_STATUS_SLEEPING})
		return True

