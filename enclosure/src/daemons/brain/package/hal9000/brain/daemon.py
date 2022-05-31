#!/usr/bin/python3

import os
import sys
import re

from configparser import ConfigParser

from paho.mqtt.publish import single as mqtt_publish_message
from hal9000.daemon import HAL9000_Daemon


class Daemon(HAL9000_Daemon):

	def __init__(self):
		HAL9000_Daemon.__init__(self, 'brain')
		self.actions = dict()
		self.triggers = dict()
		self.synapses = dict()
		self.callbacks = dict()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000_Daemon.configure(self, configuration)
		for section_name in configuration.sections():
			module_name = configuration.getstring(section_name, 'module', fallback=None)
			if module_name is not None:
				section_type, section_id = section_name.lower().split(':',1)
				if section_type == 'action':
					Action = self.import_plugin(module_name, 'Action')
					if Action is not None:
						action = Action(section_id)
						action.configure(configuration, section_name)
						self.actions[section_id] = action
				if section_type == 'trigger':
					Trigger = self.import_plugin(module_name, 'Trigger')
					if Trigger is not None:
						trigger = Trigger(section_id)
						trigger.configure(configuration, section_name)
						self.triggers[section_id] = trigger
		for synapse_name in configuration.options('synapses'):
			self.synapses[synapse_name] = list()
			actions = configuration.getlist('synapses', synapse_name)
			for action in actions:
				self.synapses[synapse_name].append(action)
		for trigger_id in self.triggers.keys():
			trigger = self.triggers[trigger_id]
			callbacks = trigger.callbacks()
			for callback_type in callbacks.keys():
				if callback_type.lower() == 'mqtt':
					callback_list = callbacks[callback_type]
					for mqtt_topic in callback_list:
						self.mqtt.subscribe(mqtt_topic)
						if 'mqtt' not in self.callbacks:
							self.callbacks['mqtt'] = dict()
						if mqtt_topic not in self.callbacks['mqtt']:
							self.callbacks['mqtt'][mqtt_topic] = list()
						self.callbacks['mqtt'][mqtt_topic].append(trigger)


	def do_loop(self) -> bool:
		return True

	
	def on_mqtt(self, client, userdata, message):
		HAL9000_Daemon.on_mqtt(self, client, userdata, message)
		if 'mqtt' in self.callbacks:
			if message.topic in self.callbacks['mqtt']:
				brain_data = dict()
				synapse_data = dict()
				for trigger in self.callbacks['mqtt'][message.topic]:
					trigger_id = str(trigger).split(':', 2)[2]
					trigger_data = trigger.handle(message)
					if trigger_data is not None:
						synapse_data[trigger_id] = trigger_data
						brain_data |= trigger_data
				for trigger_id in synapse_data.keys():
					trigger_data = synapse_data[trigger_id]
					for action_id in self.synapses[trigger_id]:
						trigger = self.triggers[trigger_id]
						action = self.actions[action_id]
						print("{} => {} / {} => {}".format(str(trigger),trigger_data,brain_data,str(action)))
						action.process(trigger_data, brain_data)


if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

