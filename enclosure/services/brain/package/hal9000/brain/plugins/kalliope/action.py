from configparser import ConfigParser as configparser_ConfigParser
from enum import StrEnum as enum_StrEnum

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, DataInvalid, RUNLEVEL, CommitPhase
from hal9000.brain.plugins.brain import STATUS as BRAIN_STATUS


class STATUS(enum_StrEnum):
	WAITING   = 'waiting'
	LISTENING = 'listening'
	THINKING  = 'thinking'
	SPEAKING  = 'speaking'
	SLEEPING  = 'sleeping'


class Action(HAL9000_Action):

	def __init__(self, action_instance: str, **kwargs) -> None:
		super().__init__('kalliope', **kwargs)
		self.addLocalNames(['audio_in', 'audio_out', 'mute'])
		self.addRemoteNames(['volume'])
		self.runlevel = DataInvalid.UNKNOWN, CommitPhase.COMMIT
		self.status = DataInvalid.UNKNOWN, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.config['initial-volume'] = configuration.getint(section_name, 'initial-volume', fallback=50)
		self.module.config['trigger-mqtt-topic'] = configuration.get(section_name, 'trigger-mqtt-topic', fallback=None)
		self.module.config['command-mqtt-topic-prefix'] = configuration.get(section_name, 'command-mqtt-topic-prefix', fallback='hal9000/command/kalliope')
		self.module.daemon.add_runlevel_inhibitor(RUNLEVEL.SYNCING, 'kalliope: kalliope.status==unknown',  self.runlevel_inhibitor_syncing_status)
		self.module.daemon.plugins['kalliope'].addSignalHandler(self.on_kalliope_signal)
		self.module.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.module.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_volume_callback, 'volume')
		self.module.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_mute_callback, 'mute')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.module.daemon.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.module.mqtt_prefix = self.module.config['command-mqtt-topic-prefix']


	async def runlevel_inhibitor_syncing_status(self) -> bool:
		if self.status not in list(STATUS):
			return False
		return True


	async def on_kalliope_signal(self, plugin: HAL9000_Plugin, signal: dict) -> None:
		if 'runlevel' in signal:
			match signal['runlevel']:
				case None | '':
					self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/runlevel', 'payload': None})
				case RUNLEVEL.KILLED:
					self.runlevel = RUNLEVEL.KILLED, CommitPhase.COMMIT
				case other:
					self.runlevel = signal['runlevel']
		if 'status' in signal:
			match signal['status']:
				case None | '':
					self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/status', 'payload': None})
				case other:
					self.status = signal['status']
		if 'command' in signal:
			if 'name' in signal['command']:
				command_name = signal['command']['name']
				self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/{command_name}', \
				                                         'payload': signal['command']['parameter'] if 'parameter' in signal['command'] else None})
		if 'volume' in signal:
			if 'level' in signal['volume']:
				if signal['volume']['level'] not in list(DataInvalid):
					if int(signal['volume']['level']) >= 0 and int(signal['volume']['level']) <= 100:
						if 'origin' in signal and signal['origin'].startswith('frontend') == True:
							if int(signal['volume']['level']) > 0 or self.mute == 'false':
								self.volume = str(signal['volume']['level']), CommitPhase.COMMIT
								self.mute = 'false', CommitPhase.COMMIT
						else:
							self.volume = str(signal['volume']['level'])
			if 'mute' in signal['volume']:
				if signal['volume']['mute'] not in list(DataInvalid):
					self.mute = str(signal['volume']['mute']).lower(), CommitPhase.COMMIT
					match self.mute:
						case 'true':
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/volume', 'payload': {'level': 0}})
						case 'false':
							if self.volume not in list(DataInvalid):
								self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/volume', \
								                                         'payload': {'level': int(self.volume)}})


	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if new_runlevel in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_runlevel not in list(RUNLEVEL):
					return False
			case CommitPhase.COMMIT:
				if old_runlevel == RUNLEVEL.KILLED:
					self.status = DataInvalid.UNKNOWN, CommitPhase.COMMIT
					self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/status', 'payload': None})
				if new_runlevel == RUNLEVEL.KILLED:
					self.status = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.audio_in = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.audio_out = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.mute = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.volume = DataInvalid.UNINITIALIZED, CommitPhase.COMMIT
					self.module.daemon.process_error('critical', '300', "System offline", f"Service 'kalliope' unavailable")
		return True


	def on_kalliope_status_callback(self, plugin: HAL9000_Plugin, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if new_status in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_status not in list(STATUS):
					return False
			case CommitPhase.COMMIT:
				if old_status in list(DataInvalid) and new_status in list(STATUS):
					self.mute = 'false'
					self.volume = str(self.module.config['initial-volume'])
				match new_status:
					case STATUS.SLEEPING:
						self.audio_in = 'none', CommitPhase.COMMIT
						self.audio_out = 'none', CommitPhase.COMMIT
						if self.module.config['trigger-mqtt-topic'] is not None:
							self.module.daemon.queue_signal('mqtt', {'topic': self.module.config['trigger-mqtt-topic'], 'payload': 'pause'})
					case STATUS.WAITING:
						self.audio_in = 'wake-word-detector', CommitPhase.COMMIT
						self.audio_out = 'none', CommitPhase.COMMIT
						if self.module.config['trigger-mqtt-topic'] is not None:
							self.module.daemon.queue_signal('mqtt', {'topic': self.module.config['trigger-mqtt-topic'], 'payload': 'unpause'})
					case STATUS.LISTENING:
						self.audio_in = 'speech-to-text', CommitPhase.COMMIT
						self.audio_out = 'none', CommitPhase.COMMIT
					case STATUS.THINKING:
						self.audio_in = 'none', CommitPhase.COMMIT
						self.audio_out = 'none', CommitPhase.COMMIT
					case STATUS.SPEAKING:
						self.audio_in = 'none', CommitPhase.COMMIT
						self.audio_out = 'text-to-speech', CommitPhase.COMMIT
		return True


	def on_kalliope_volume_callback(self, plugin: HAL9000_Plugin, key: str, old_volume: str, new_volume: str, phase: CommitPhase) -> bool:
		if new_volume in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if self.mute == 'true':
					self.module.daemon.logger.info(f"[kalliope] rejecting volume change request due to being muted")
					return False
				if int(new_volume) < 0 or int(new_volume) > 100:
					self.module.daemon.logger.info(f"[kalliope] rejecting volume change request due to invalid value '{new_volume}'")
					return False
			case CommitPhase.REMOTE_REQUESTED:
				self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/volume', 'payload': {'level': int(new_volume)}})
		return True


	def on_kalliope_mute_callback(self, plugin: HAL9000_Plugin, key: str, old_mute: str, new_mute: str, phase: CommitPhase) -> bool:
		if new_mute in list(DataInvalid):
			return True
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_mute not in ['true', 'false']:
					self.module.daemon.logger.info(f"[kalliope] inhibiting change of mute from '{old_mute}' to '{new_mute}'")
					return False
				match new_mute:
					case 'true':
						self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/volume', \
						                                         'payload': {'level': 0}})
					case 'false':
						if self.volume not in list(DataInvalid):
							self.module.daemon.queue_signal('mqtt', {'topic': f'{self.module.mqtt_prefix}/volume', \
							                                         'payload': {'level': int(self.volume)}})
		return True


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT and new_runlevel == RUNLEVEL.SYNCING:
			self.module.daemon.queue_signal('kalliope', {'volume': {'level': self.module.config['initial-volume'], 'mute': False}})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			match new_status:
				case BRAIN_STATUS.AWAKE:
					self.module.daemon.queue_signal('kalliope', {'status': str(STATUS.WAITING)})
				case BRAIN_STATUS.ASLEEP:
					self.module.daemon.queue_signal('kalliope', {'status': str(STATUS.SLEEPING)})
		return True

