#!/usr/bin/python3

import os
import sys
import time
import re
import json

from datetime import datetime, date, timedelta, time as timeformat
from configparser import ConfigParser

from paho.mqtt.publish import single as mqtt_publish_message
from hal9000.daemon import HAL9000_Daemon
from .modules import HAL9000_Module


class ConfigurationError:
	pass


class Daemon(HAL9000_Daemon):

	CONSCIOUSNESS_AWAKE = 'awake'
	CONSCIOUSNESS_ASLEEP = 'asleep'
	CONSCIOUSNESS_VALID = [CONSCIOUSNESS_AWAKE, CONSCIOUSNESS_ASLEEP]

	def __init__(self) -> None:
		HAL9000_Daemon.__init__(self, 'brain')
		self.cortex = dict()
		self.cortex['brain'] = dict()
		self.cortex['brain']['consciousness'] = Daemon.CONSCIOUSNESS_ASLEEP
		self.cortex['brain']['activity'] = dict()
		self.cortex['brain']['activity']['voice-assistant'] = None
		self.cortex['brain']['activity']['enclosure'] = dict()
		self.cortex['brain']['activity']['enclosure']['audio'] = None
		self.cortex['brain']['activity']['enclosure']['gui'] = dict()
		self.cortex['brain']['activity']['enclosure']['gui']['screen'] = None
		self.cortex['brain']['activity']['enclosure']['gui']['overlay'] = None
		self.actions = dict()
		self.triggers = dict()
		self.synapses = dict()
		self.callbacks = dict()
		self.timeouts = dict()
		self.booting_timeout = None
		self.booting_modules = dict()
		self.actions_queued = list()


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000_Daemon.configure(self, configuration)
		self.config['boot-timeout']  = configuration.getint('brain', 'boot-timeout', fallback=10)
		self.config['boot-finished-mqtt-topic']  = configuration.get('brain', 'boot-finished-mqtt-topic', fallback=None)
		self.config['error-database-base-url']  = configuration.get('help', 'error-database-base-url', fallback=None)
		self.config['sleep-time']  = configuration.get('brain', 'sleep-time', fallback=None)
		self.config['wakeup-time'] = configuration.get('brain', 'wakeup-time', fallback=None)
		if self.config['sleep-time'] == self.config['wakeup-time']:
			#TODO: error message
			raise ConfigurationError
		self.mqtt.subscribe('hal9000/daemon/brain/consciousness/state')
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
						self.logger.debug("mqtt.subscribe('{}') for trigger '{}'".format(mqtt_topic, trigger_id))
						self.mqtt.subscribe(mqtt_topic)
		self.logger.debug("CORTEX at startup = {}".format(self.cortex))


	def loop(self) -> None:
		self.booting_timeout = datetime.now() + timedelta(seconds=self.config['boot-timeout'])
		for module in list(self.triggers.values()) + list(self.actions.values()):
			cortex = self.cortex.copy()
			if module.runlevel(cortex) == HAL9000_Module.MODULE_RUNLEVEL_BOOTING:
				self.booting_modules[str(module)] = module
		datetime_now = datetime.now()
		datetime_sleep = None
		datetime_wakeup = None
		if self.config['sleep-time'] is not None and self.config['wakeup-time'] is not None:
			datetime_sleep = datetime.combine(date.today(), timeformat.fromisoformat(self.config['sleep-time']))
			if(datetime_now > datetime_sleep):
				datetime_sleep += timedelta(hours=24)
			self.timeouts[Daemon.CONSCIOUSNESS_ASLEEP] = datetime_sleep, None
			datetime_wakeup = datetime.combine(date.today(), timeformat.fromisoformat(self.config['wakeup-time']))
			if(datetime_now > datetime_wakeup):
				datetime_wakeup += timedelta(hours=24)
			self.timeouts[Daemon.CONSCIOUSNESS_AWAKE] = datetime_wakeup, None
		if datetime_wakeup == datetime_sleep or datetime_sleep < datetime_wakeup:
			self.set_consciousness(Daemon.CONSCIOUSNESS_AWAKE)
		HAL9000_Daemon.loop(self)

	
	def do_loop(self) -> bool:
		if self.booting_timeout is not None:
			for id in list(self.booting_modules.keys()):
				cortex = self.cortex.copy()
				if self.booting_modules[id].runlevel(cortex) != HAL9000_Module.MODULE_RUNLEVEL_BOOTING:
					del self.booting_modules[id]
			if datetime.now() > self.booting_timeout:
				self.booting_timeout = None
				self.logger.warn("Booting completed (modules that haven't finished bootup: {})". format(", ".join(self.booting_modules.keys())))
				for id in self.booting_modules.keys():
					error = self.booting_modules[id].runlevel_error(self.cortex.copy())
					self.logger.warn("Error #{} for module '{}': {}".format(error['code'], id, error['message']))
#TODO					if self.config['error-message-translation-file'] is not None:
#TODO						error['message'] = self.translate(error['message'], self.config['error-message-translation-file'])
					if self.config['error-database-base-url'] is not None:
						error['url'] = self.config['error-database-base-url'] + error['code']
					if "image" in error and error["image"] is not None:
						self.arduino_show_gui_screen('error', error) #TODO
					if "audio" in error and error["audio"] is not None:
						self.kalliope_play_audio(error["audio"]) #TODO

			if len(self.booting_modules) == 0:
				self.booting_timeout = None
				self.logger.info("Booting completed for all modules")
				if self.config['boot-finished-mqtt-topic'] is not None:
					mqtt_publish_message(self.config['boot-finished-mqtt-topic'])
		for key in self.timeouts.copy().keys():
			timeout, data = self.timeouts[key]
			if datetime.now() > timeout:
				if key in Daemon.CONSCIOUSNESS_VALID:
					self.timeouts[key] = timeout+timedelta(hours=24), data
					self.set_consciousness(key)
				if key == 'screen':
					del self.timeouts[key]
					self.arduino_show_gui_screen(data, {})
				if key == 'overlay':
					del self.timeouts[key]
					self.arduino_hide_gui_overlay(data)
		return True

	
	def on_mqtt(self, client, userdata, message) -> None:
		HAL9000_Daemon.on_mqtt(self, client, userdata, message)
		if message.topic == 'hal9000/daemon/brain/consciousness/state':
			consciousness_state = message.payload.decode('utf-8')
			if consciousness_state in Daemon.CONSCIOUSNESS_VALID:
				self.set_consciousness(consciousness_state)
			return
		if self.cortex['brain']['consciousness'] == Daemon.CONSCIOUSNESS_AWAKE:
			if 'mqtt' in self.callbacks and message.topic in self.callbacks['mqtt']:
				self.logger.info("SYNAPSES fired: {}".format(', '.join(str(x).split(':',2)[2] for x in self.callbacks['mqtt'][message.topic])))
				self.logger.debug("CORTEX before triggers = {}".format(self.cortex))
				signals = dict()
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
				self.logger.debug("CORTEX after actions   = {}".format(self.cortex))


	def queue_action(self, action_name, signal_data) -> None:
		self.actions_queued.append([action_name, signal_data])


	def process_queued_actions(self) -> None:
		for action_name, signal_data in self.actions_queued:
			if action_name in self.actions:
				cortex = self.cortex.copy()
				self.actions[action_name].process(signal_data, cortex)
				if action_name in cortex:
					self.cortex[action_name] = cortex[action_name]
		self.actions_queued.clear()


	def set_consciousness(self, new_state) -> None:
		if new_state in Daemon.CONSCIOUSNESS_VALID:
			old_state = self.cortex['brain']['consciousness']
			self.logger.info("CONSCIOUSNESS state changing from '{}' to '{}'".format(old_state, new_state))
			self.logger.debug("CORTEX before state change = {}".format(self.cortex))
			self.cortex['brain']['consciousness'] = new_state
			for action_name in self.actions.keys():
				signal = {"brain": {"consciousness": new_state}}
				cortex = self.cortex.copy()
				self.actions[action_name].process(signal, cortex)
				if action_name in cortex:
					self.cortex[action_name] = cortex[action_name]
			self.process_queued_actions()
			self.logger.debug("CORTEX after state change  = {}".format(self.cortex))


	def arduino_show_gui_screen(self, screen, parameter) -> None:
		self.cortex['brain']['activity']['enclosure']['gui']['screen'] = screen
		self.arduino_send_command('gui/screen', json.dumps({screen: parameter}))


	def arduino_hide_gui_screen(self, screen, parameter) -> None:
		if self.cortex['brain']['activity']['enclosure']['gui']['screen'] == screen:
			self.cortex['brain']['activity']['enclosure']['gui']['screen'] = None
			self.arduino_send_command('gui/screen', json.dumps({'idle': {}}))


	def arduino_show_gui_overlay(self, overlay, parameter) -> None:
		self.cortex['brain']['activity']['enclosure']['gui']['overlay'] = overlay
		self.arduino_send_command('gui/overlay', json.dumps({overlay: parameter}))


	def arduino_hide_gui_overlay(self, overlay) -> None:
		if self.cortex['brain']['activity']['enclosure']['gui']['overlay'] == overlay:
			self.cortex['brain']['activity']['enclosure']['gui']['overlay'] = None
			self.arduino_send_command('gui/screen', json.dumps({'none': {}}))


	def arduino_set_system_time(self) -> None:
		self.arduino_send_command("system/time", json.dumps({"config": {"epoch": int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds)}}))
		if self.config['sleep-time'] != self.config['wakeup-time']:
			self.arduino_set_system_setting('system/state:time/sleep',  self.config['sleep-time'])
			self.arduino_set_system_setting('system/state:time/wakeup', self.config['wakeup-time'])
			self.arduino_save_system_setting()


	def arduino_set_system_runtime(self, key, value) -> None:
		self.arduino_send_command('system/runtime', json.dumps({"set": {"key": key, "value": value}}))


	def arduino_set_system_setting(self, key, value) -> None:
		self.arduino_send_command('system/settings', json.dumps({"set": {"key": key, "value": value}}))


	def arduino_save_system_setting(self) -> None:
		self.arduino_send_command('system/settings', json.dumps({"save": {}}))


	def arduino_set_device_display(self, parameter) -> None:
		self.arduino_send_command("device/display", json.dumps({"display": {"data": parameter}}))


	def arduino_system_reset(self) -> None:
		self.arduino_send_command("system/reset", json.dumps({}))


	def arduino_send_command(self, topic, body) -> None:
		mqtt_publish_message(f"hal9000/command/arduino/{topic}", body)


	def kalliope_play_audio(self, filename) -> None:
		pass


if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

