import os
import json
from configparser import ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, HAL9000_Plugin_Cortex


class Action(HAL9000_Action):
	def __init__(self, action_name: str, plugin_cortex, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'mqtt', action_name, plugin_cortex, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		self.daemon.cortex['plugin']['mqtt'].addSignalHandler(self.on_mqtt_signal)


	def runlevel(self) -> str:
		return HAL9000_Plugin.PLUGIN_RUNLEVEL_RUNNING


	def on_mqtt_signal(self, plugin, signal):
		messages = signal
		if isinstance(messages, list) is False:
			messages = [messages]
		for message in messages:
			mqtt_topic = message['topic']
			mqtt_payload = message['payload']
			if isinstance(mqtt_payload, str) is False:
				mqtt_payload = json.dumps(mqtt_payload)
			self.daemon.mqtt.publish(mqtt_topic, mqtt_payload)

