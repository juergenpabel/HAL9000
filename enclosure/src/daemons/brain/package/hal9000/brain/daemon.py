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

		self.cortex['brain'] = dict()
		self.cortex['brain']['consciousness'] = Daemon.CONSCIOUSNESS_AWAKE
		self.cortex['brain']['activity'] = dict()
		self.cortex['brain']['activity']['voice-assistant'] = None
		self.cortex['brain']['activity']['enclosure'] = dict()
		self.cortex['brain']['activity']['enclosure']['audio'] = None
		self.cortex['brain']['activity']['enclosure']['gui'] = dict()
		self.cortex['brain']['activity']['enclosure']['gui']['screen'] = None
		self.cortex['brain']['activity']['enclosure']['gui']['overlay'] = None
		self.cortex['enclosure'] = dict()
		self.actions = dict()
		self.triggers = dict()
		self.synapses = dict()
		self.callbacks = dict()
		self.timeouts = dict()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000_Daemon.configure(self, configuration)
		self.mqtt.subscribe('{}/brain/consciousness/+'.format(self.config['mqtt-topic-base']))
		for section_name in configuration.sections():
			module_path = configuration.getstring(section_name, 'module', fallback=None)
			if module_path is not None:
				module_type, module_id = section_name.lower().split(':',1)
				if module_type == 'action':
					Action = self.import_plugin(module_path, 'Action')
					if Action is not None:
						cortex = self.cortex.copy()
						action = Action(module_id, daemon=self)
						action.configure(configuration, section_name, cortex)
						self.actions[module_id] = action
						if module_id in cortex:
							self.cortex[module_id] = cortex[module_id]
				if module_type == 'trigger':
					Trigger = self.import_plugin(module_path, 'Trigger')
					if Trigger is not None:
						trigger = Trigger(module_id)
						trigger.configure(configuration, section_name)
						self.triggers[module_id] = trigger
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
		self.logger.debug("CORTEX at startup = {}".format(self.cortex))


	def loop(self) -> None:
		self.set_device_display({"backlight": "on"})
		#TODO: signal ready
		HAL9000_Daemon.loop(self)

	
	def do_loop(self) -> bool:
		for key in self.timeouts.copy().keys():
			timeout, data = self.timeouts[key]
			if datetime.now() > timeout:
				if key == 'consciousness':
					self.set_consciousness(data)
					del self.timeouts[key]
				if key == 'overlay':
					self.hide_gui_overlay(data)
					del self.timeouts[key]
		return True

	
	def on_mqtt(self, client, userdata, message):
		HAL9000_Daemon.on_mqtt(self, client, userdata, message)
		if message.topic.startswith('{}/brain/consciousness/'.format(self.config['mqtt-topic-base'])):
			if message.topic == '{}/brain/consciousness/state'.format(self.config['mqtt-topic-base']):
				state = message.payload.decode('utf-8')
				if state in Daemon.CONSCIOUSNESS_VALID:
					self.logger.info("CONSCIOUSNESS state changing from '{}' to '{}'".format(self.cortex['brain']['consciousness'], state))
					self.cortex['brain']['consciousness'] = state
			return
		signals = dict()
		if self.cortex['brain']['consciousness'] == Daemon.CONSCIOUSNESS_AWAKE:
			if 'mqtt' in self.callbacks and message.topic in self.callbacks['mqtt']:
				self.logger.info("SYNAPSES fired: {}".format(', '.join(str(x).split(':',2)[2] for x in self.callbacks['mqtt'][message.topic])))
				self.logger.debug("CORTEX before triggers = {}".format(self.cortex))
				for trigger in self.callbacks['mqtt'][message.topic]:
					signal = trigger.handle(message)
					if signal is not None:
						synapse_name = str(trigger).split(':', 2)[2]
						signals[synapse_name] = signal
				for synapse_name in signals.keys():
					signal = signals[synapse_name]
					self.logger.debug("SIGNAL generated from triggers = {}".format(signal))
					for action_name in self.synapses[synapse_name]:
						cortex = self.cortex.copy()
						self.actions[action_name].process(signal, cortex)
						if action_name in cortex:
							self.cortex[action_name] = cortex[action_name]
				self.process_queued_actions()
				self.logger.debug("CORTEX after actions =   {}".format(self.cortex))


	def queue_action(self, action_name, signal_data) -> None:
		self.timeouts['action-{}'.format(int(datetime.now().timestamp()))] = datetime.now(), [action_name, signal_data]


	def process_queued_actions(self) -> None:
		for key in self.timeouts.copy().keys():
			cortex = self.cortex.copy()
			timeout, data = self.timeouts[key]
			if key.startswith('action-'):
				[action_name, signal] = data
				if action_name in self.actions:
					self.actions[action_name].process(signal, cortex)
					if action_name in self.cortex:
						self.cortex[action_name] = cortex[action_name]
				del self.timeouts[key]


	def set_consciousness(self, new_state) -> None:
		if new_state in Daemon.CONSCIOUSNESS_VALID:
			old_state = self.cortex['brain']['consciousness']
			self.logger.info("CONSCIOUSNESS state changing from '{}' to '{}'".format(old_state, new_state))
			self.cortex['brain']['consciousness'] = new_state
			if new_state == "awake":
				self.set_device_display({"backlight": "on"})
			else:
				self.set_device_display({"backlight": "off"})


	def show_gui_screen(self, screen, parameter) -> None:
		self.cortex['brain']['activity']['enclosure']['gui']['screen'] = screen
		self.set_gui_screen(screen, 'show', parameter)


	def hide_gui_screen(self, screen, parameter) -> None:
		if self.cortex['brain']['activity']['enclosure']['gui']['screen'] == screen:
			self.cortex['brain']['activity']['enclosure']['gui']['screen'] = None
			self.set_gui_screen('idle', 'show', {})


	def set_gui_screen(self, screen, action, parameter) -> None:
		mqtt_publish_message('{}/enclosure/gui/screen'.format(self.config['mqtt-topic-base']), json.dumps({"screen": {screen: action, "data": parameter}}))


	def show_gui_overlay(self, overlay, parameter) -> None:
		self.cortex['brain']['activity']['enclosure']['gui']['overlay'] = overlay
		self.set_gui_overlay(overlay, 'show', parameter)


	def hide_gui_overlay(self, overlay) -> None:
		if self.cortex['brain']['activity']['enclosure']['gui']['overlay'] == overlay:
			self.cortex['brain']['activity']['enclosure']['gui']['overlay'] = None
			self.set_gui_overlay(overlay, 'hide', None)


	def set_gui_overlay(self, overlay, action, parameter) -> None:
		mqtt_publish_message('{}/enclosure/gui/overlay'.format(self.config['mqtt-topic-base']), json.dumps({"overlay": {overlay: action, "data": parameter}}))


	def set_device_display(self, parameter) -> None:
		mqtt_publish_message('{}/enclosure/device/display'.format(self.config['mqtt-topic-base']), json.dumps({"display": {"data": parameter}}))


	def arduino_system_reset(self) -> None:
		mqtt_publish_message('{}/enclosure/system/reset'.format(self.config['mqtt-topic-base']), json.dumps({}))


if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

