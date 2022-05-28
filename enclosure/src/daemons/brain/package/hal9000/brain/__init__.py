#!/usr/bin/python3

import os
import sys
import re

from configparser import ConfigParser

from paho.mqtt.publish import single as mqtt_publish_message
from hal9000.daemon import HAL9000_Daemon as HAL9000
from hal9000.abstract.plugin import HAL9000_PluginManager as PluginManager


class Daemon(HAL9000):

	def __init__(self):
		HAL9000.__init__(self, 'brain')
		self.plugin_manager = PluginManager()
		self.mqtt_callbacks = dict()
		self.actions = dict()
		self.triggers = dict()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		for section_name in configuration.sections():
			module_name = configuration.getstring(section_name, 'module', fallback=None)
			if module_name is not None:
				section_type, section_id = section_name.lower().split(':',1)
				if section_type == 'action':
					action = self.plugin_manager.load_action(module_name)
					action.configure(configuration, section_name)
					self.actions[module_name] = action
				if section_type == 'trigger':
					trigger = self.plugin_manager.load_trigger(module_name)
					trigger.configure(configuration, section_name)
					for mqtt_topic in trigger.callbacks():
						self.mqtt.subscribe(mqtt_topic)
						self.mqtt_callbacks[mqtt_topic] = trigger.handle
					self.triggers[module_name] = trigger
			


	def do_loop(self) -> bool:
		return True

	
	def on_mqtt(self, client, userdata, message):
		print("yeay")
		HAL9000.on_mqtt(self, client, userdata, message)
		if message.topic in self.mqtt_callbacks:
			callback = self.mqtt_callbacks[message.topic]
			data = callback(message)



if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

