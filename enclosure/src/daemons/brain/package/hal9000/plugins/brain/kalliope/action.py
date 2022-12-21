#!/usr/bin/python3

from configparser import ConfigParser
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain.modules import HAL9000_Action
from hal9000.brain.daemon import Daemon


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
			return Action.MODULE_RUNLEVEL_BOOTING
		return Action.MODULE_RUNLEVEL_RUNNING


	def runlevel_error(self, cortex: dict) -> dict:
		return {"code": "002",
		        "level": "error",
		        "message": "No connection to kalliope. Voice commands will not work.",
		        "audio": None,
		        "image": "error/002-kalliope.png"}


	def process(self, signal: dict, cortex: dict) -> None:
		if 'brain' in signal:
			if 'consciousness' in signal['brain']:
				brain_state = signal['brain']['consciousness']
				if brain_state == Daemon.CONSCIOUSNESS_AWAKE:
					if self.config['kalliope-trigger-multiplexer-mqtt-topic'] is not None:
						mqtt_publish_message(self.config['kalliope-trigger-multiplexer-mqtt-topic'], "unpause")
				if brain_state == Daemon.CONSCIOUSNESS_ASLEEP:
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
					if cortex['brain']['consciousness'] == Daemon.CONSCIOUSNESS_AWAKE:
						if kalliope_state == Action.KALLIOPE_STATE_LISTENING:
							self.daemon.arduino_show_gui_screen('hal9000', {"queue": "replace", "sequence": {"name": "wakeup", "loop": "false"}})
							self.daemon.arduino_show_gui_screen('hal9000', {"queue": "append",  "sequence": {"name": "active", "loop": "true"}})
						if kalliope_state == Action.KALLIOPE_STATE_WAITING:
							self.daemon.arduino_show_gui_screen('hal9000', {"queue": "replace", "sequence": {"name": "sleep",  "loop": "false"}})
							self.daemon.cortex['#activity']['video'].screen = 'none'
					if cortex['brain']['consciousness'] == Daemon.CONSCIOUSNESS_ASLEEP:
						if self.config['kalliope-trigger-multiplexer-mqtt-topic'] is not None:
							mqtt_publish_message(self.config['kalliope-trigger-multiplexer-mqtt-topic'], "pause")

