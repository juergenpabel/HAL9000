#!/usr/bin/python3

import os
import sys
import re
import json

from datetime import datetime, timedelta
from configparser import ConfigParser

from paho.mqtt.publish import single as mqtt_publish_message
from hal9000.daemon import HAL9000_Daemon


class Daemon(HAL9000_Daemon):

	CONSCIOUSNESS_AWAKE = 'awake'
	CONSCIOUSNESS_ASLEEP = 'asleep'
	CONSCIOUSNESS_VALID = [CONSCIOUSNESS_AWAKE, CONSCIOUSNESS_ASLEEP]

	def __init__(self):
		HAL9000_Daemon.__init__(self, 'brain')
		self.cortex = dict()

		self.cortex['daemon'] = dict()
		self.cortex['daemon']['consciousness'] = Daemon.CONSCIOUSNESS_AWAKE

		self.cortex['enclosure'] = dict()
		#TODO check if rfid installed
		self.cortex['enclosure']['rfid'] = dict()
		self.cortex['enclosure']['rfid']['uid'] = None
		#TODO check if volume rotary installed
		#TODO check if control rotary installed
		self.cortex['enclosure']['control'] = dict()
		#TODO check if button installed
		self.cortex['enclosure']['button'] = dict()
		#TODO check if motion installed
		self.cortex['enclosure']['motion'] = dict()

		self.actions = dict()
		self.triggers = dict()
		self.synapses = dict()
		self.callbacks = dict()
		self.timeouts = dict()


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
						action.configure(configuration, section_name, self.cortex)
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
						if 'mqtt' not in self.callbacks:
							self.callbacks['mqtt'] = dict()
						if mqtt_topic not in self.callbacks['mqtt']:
							self.callbacks['mqtt'][mqtt_topic] = list()
						self.callbacks['mqtt'][mqtt_topic].append(trigger)
						self.mqtt.subscribe(mqtt_topic)


	def loop(self) -> None:
		self.set_display_status('init')
		#TODO: signal ready
		HAL9000_Daemon.loop(self)

	
	def do_loop(self) -> bool:
		for key in self.timeouts.copy().keys():
			timeout, data = self.timeouts[key]
			if datetime.now() > timeout:
#				if key == 'fsm:wakeup':
#					self.do_wakeup(data)
#				if key == 'fsm:sleep':
#					self.do_sleep(data)
				if key == 'overlay':
					self.hide_display_overlay(data)
				del self.timeouts[key]
		return True

	
	def on_mqtt(self, client, userdata, message):
		HAL9000_Daemon.on_mqtt(self, client, userdata, message)
		signals = dict()
		cortex = self.cortex.copy()
		if 'mqtt' in self.callbacks:
			if message.topic in self.callbacks['mqtt']:
				self.logger.info("SYNAPSES fired: {}".format(', '.join(str(x).split(':',2)[2] for x in self.callbacks['mqtt'][message.topic])))
				self.logger.debug("CORTEX before triggers = {}".format(self.cortex))
				for trigger in self.callbacks['mqtt'][message.topic]:
					signal = trigger.handle(message)
					if signal is not None:
						synapse_name = str(trigger).split(':', 2)[2]
						signals[synapse_name] = signal
				for synapse_name in signals.keys():
					signal = signals[synapse_name]
					for action_name in self.synapses[synapse_name]:
						action = self.actions[action_name]
						if str(action) == 'action:hal9000:self':
							signal['daemon'] = self
						memory = action.process(signal, cortex)
						if str(action) == 'action:hal9000:self':
							del signal['daemon']
						if memory is not None:
							self.cortex |= memory
				self.logger.debug("CORTEX after actions = {}".format(self.cortex))


	def show_display_overlay(self, overlay, data = None) -> None:
		self.set_display_overlay(overlay, 'show', data)


	def hide_display_overlay(self, overlay) -> None:
		self.set_display_overlay(overlay, 'hide', None)


	def set_display_overlay(self, overlay, action, parameter) -> None:
		mqtt_publish_message('{}/enclosure/gui/overlay'.format(self.config['mqtt-topic-base']), json.dumps({"overlay": {overlay: action, "data": parameter}}))


	def set_display_status(self, status) -> None:
		mqtt_publish_message('{}/enclosure/device/display'.format(self.config['mqtt-topic-base']), status)


if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

