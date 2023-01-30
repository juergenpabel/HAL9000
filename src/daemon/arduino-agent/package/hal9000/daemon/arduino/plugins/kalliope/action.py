#!/usr/bin/python3

from configparser import ConfigParser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.daemon.arduino.modules import HAL9000_Action
from hal9000.daemon.arduino.daemon import Daemon


class Action(HAL9000_Action):

	KALLIOPE_STATE_UNKNOWN   = 'unknown'
	KALLIOPE_STATE_READY     = 'ready'
	KALLIOPE_STATE_WAITING   = 'waiting'
	KALLIOPE_STATE_LISTENING = 'listening'
	KALLIOPE_STATE_THINKING  = 'thinking'
	KALLIOPE_STATE_SPEAKING  = 'speaking'
	KALLIOPE_STATES_VALID = [KALLIOPE_STATE_WAITING, KALLIOPE_STATE_LISTENING, KALLIOPE_STATE_THINKING, KALLIOPE_STATE_SPEAKING]


	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'kalliope', action_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		self.config['kalliope-trigger-multiplexer-mqtt-topic'] = configuration.get(section_name, 'kalliope-trigger-multiplexer-mqtt-topic', fallback=None)
		cortex['kalliope'] = dict()
		cortex['kalliope']['state'] = Action.KALLIOPE_STATE_UNKNOWN


	def runlevel(self, cortex: dict) -> str:
		if cortex['kalliope']['state'] == Action.KALLIOPE_STATE_UNKNOWN:
			return Action.MODULE_RUNLEVEL_STARTING
		return Action.MODULE_RUNLEVEL_RUNNING


	def runlevel_error(self, cortex: dict) -> dict:
		return {"code": "TODO",
		        "level": "error",
		        "message": "No connection to kalliope. Voice commands will not work.",
		        "audio": None}


	def process(self, signal: dict, cortex: dict) -> None:
		if 'agent' in signal:
			if 'consciousness' in signal['agent']:
				agent_state = signal['agent']['consciousness']
				if agent_state == Daemon.CONSCIOUSNESS_AWAKE:
					if self.config['kalliope-trigger-multiplexer-mqtt-topic'] is not None:
						mqtt_publish_message(self.config['kalliope-trigger-multiplexer-mqtt-topic'], "unpause")
				if agent_state == Daemon.CONSCIOUSNESS_ASLEEP:
					if self.config['kalliope-trigger-multiplexer-mqtt-topic'] is not None:
						mqtt_publish_message(self.config['kalliope-trigger-multiplexer-mqtt-topic'], "pause")
		if 'kalliope' in signal:
			if 'state' in signal['kalliope']:
				kalliope_state = signal['kalliope']['state']
				if cortex['kalliope']['state'] == Action.KALLIOPE_STATE_UNKNOWN:
					if kalliope_state == Action.KALLIOPE_STATE_READY:
						cortex['kalliope']['state'] = Action.KALLIOPE_STATE_READY
					elif kalliope_state in Action.KALLIOPE_STATES_VALID:
						cortex['kalliope']['state'] = kalliope_state
					return
				if kalliope_state in Action.KALLIOPE_STATES_VALID:
					cortex['kalliope']['state'] = kalliope_state
					if cortex['#consciousness'] == Daemon.CONSCIOUSNESS_AWAKE:
						if kalliope_state == Action.KALLIOPE_STATE_LISTENING:
							self.daemon.video_gui_screen_show('hal9000', {"queue": "replace", "sequence": {"name": "wakeup", "loop": "false"}})
							self.daemon.video_gui_screen_show('hal9000', {"queue": "append",  "sequence": {"name": "active", "loop": "true"}})
						if kalliope_state == Action.KALLIOPE_STATE_WAITING:
							self.daemon.video_gui_screen_show('hal9000', {"queue": "replace", "sequence": {"name": "sleep",  "loop": "false"}})
							self.daemon.cortex['#activity']['video'].screen = 'idle'
					if cortex['#consciousness'] == Daemon.CONSCIOUSNESS_ASLEEP:
						if self.config['kalliope-trigger-multiplexer-mqtt-topic'] is not None:
							mqtt_publish_message(self.config['kalliope-trigger-multiplexer-mqtt-topic'], "pause")

