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


class Activity:
	def __init__(self, module: str=None, **kwargs):
		if module is not None:
			self.module = module
		for key, value in kwargs.items():
			setattr(self, key, value)
	def __getattr__(self, item):
		return 'none'
	def __repr__(self):
		result = "{"
		result += f"module='{self.module}'"
		for key, value in self.__dict__.items():
			result += f", {key}='{value}'"
		result += "}"
		return result


class ConfigurationError:
	pass


class Daemon(HAL9000_Daemon):

	CONSCIOUSNESS_AWAKE = 'awake'
	CONSCIOUSNESS_ASLEEP = 'asleep'
	CONSCIOUSNESS_VALID = [CONSCIOUSNESS_AWAKE, CONSCIOUSNESS_ASLEEP]

	def __init__(self) -> None:
		HAL9000_Daemon.__init__(self, 'brain')
		self.cortex = dict()
		self.cortex['#consciousness'] = Daemon.CONSCIOUSNESS_ASLEEP
		self.cortex['#activity'] = dict()
		self.cortex['#activity']['audio'] = Activity()
		self.cortex['#activity']['video'] = Activity()
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
		self.config['boot-timeout']  = configuration.getint('runlevel', 'boot-timeout', fallback=10)
		self.config['boot-finished-action-name']  = configuration.get('runlevel', 'boot-finished-action-name', fallback=None)
		self.config['boot-finished-signal-data']  = configuration.get('runlevel', 'boot-finished-signal-data', fallback=None)
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
		self.booting_timeout = time.monotonic() + self.config['boot-timeout']
		for module in list(self.triggers.values()) + list(self.actions.values()):
			cortex = self.cortex.copy()
			if module.runlevel(cortex) == HAL9000_Module.MODULE_RUNLEVEL_BOOTING:
				self.booting_modules[str(module)] = module
		self.set_system_time(datetime.now())
		HAL9000_Daemon.loop(self)

	
	def do_loop(self) -> bool:
		if self.booting_timeout is not None:
			for id in list(self.booting_modules.keys()):
				cortex = self.cortex.copy()
				if self.booting_modules[id].runlevel(cortex) != HAL9000_Module.MODULE_RUNLEVEL_BOOTING:
					del self.booting_modules[id]
			if time.monotonic() > self.booting_timeout:
				self.booting_timeout = None
				self.logger.warn("Startup completed (modules that haven't finished startup: {})". format(", ".join(self.booting_modules.keys())))
				for id in self.booting_modules.keys():
					error = self.booting_modules[id].runlevel_error(self.cortex.copy())
					self.logger.warn("Error #{} for module '{}': {}".format(error['code'], id, error['message']))
#TODO					if self.config['error-message-translation-file'] is not None:
#TODO						error['message'] = self.translate(error['message'], self.config['error-message-translation-file'])
					if self.config['error-database-base-url'] is not None:
						error['url'] = self.config['error-database-base-url'] + error['code']
					if "image" in error and error["image"] is not None:
						self.show_gui_screen('error', error) #TODO
					if "audio" in error and error["audio"] is not None:
						self.kalliope_play_audio(error["audio"]) #TODO
			if len(self.booting_modules) == 0:
				self.logger.info("Startup completed for all modules ({:.2f} seconds)".format(time.monotonic()-(self.booting_timeout-self.config['boot-timeout'])))
				self.booting_timeout = None
				if self.cortex['#consciousness'] == Daemon.CONSCIOUSNESS_AWAKE:
					action_name = self.config['boot-finished-action-name']
					if action_name in self.actions:
						self.queue_signal(action_name, json.loads(self.config['boot-finished-signal-data']))
				self.show_gui_screen('idle', '')
		self.process_queued_signals()
		self.process_timeouts()
		return True

	
	def on_mqtt(self, client, userdata, message) -> None:
		HAL9000_Daemon.on_mqtt(self, client, userdata, message)
		if message.topic == 'hal9000/daemon/brain/consciousness/state':
			consciousness_state = message.payload.decode('utf-8')
			if consciousness_state in Daemon.CONSCIOUSNESS_VALID:
				self.set_consciousness(consciousness_state)
			return
		if self.cortex['#consciousness'] == Daemon.CONSCIOUSNESS_AWAKE or self.booting_timeout is not None:
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
				self.logger.debug("CORTEX after actions   = {}".format(self.cortex))
				self.process_queued_signals()


	def queue_signal(self, action_name, signal_data) -> None:
		self.actions_queued.append([action_name, signal_data])


	def process_queued_signals(self) -> None:
		actions_queued = self.actions_queued.copy()
		self.actions_queued.clear()
		if len(actions_queued) > 0:
			self.logger.debug("CORTEX before (postponed) signals = {}".format(self.cortex))
			for action_name, signal_data in actions_queued:
				self.logger.debug("Processing (postponed) signal '{}'".format(signal_data))
				action_handlers = []
				if action_name == '*':
					action_handlers = self.actions.keys()
				else:
					action_handlers.append(action_name)
				for action_handler in action_handlers:
					if action_handler in self.actions:
						cortex = self.cortex.copy()
						self.actions[action_handler].process(signal_data, cortex)
						if action_handler in cortex:
							self.cortex[action_handler] = cortex[action_handler]
			self.logger.debug("CORTEX after  (postponed) signals = {}".format(self.cortex))


	def set_timeout(self, timeout_seconds, timeout_key, timeout_data) -> None:
		self.timeouts[timeout_key] = datetime.now()+timedelta(seconds=timeout_seconds), timeout_data


	def process_timeouts(self) -> None:
		for key in self.timeouts.copy().keys():
			timeout, data = self.timeouts[key]
			if datetime.now() > timeout:
				if key in Daemon.CONSCIOUSNESS_VALID:
					self.set_consciousness(key)
					self.set_timeout(86400, key, data)
				if key == 'action':
					self.queue_signal(data[0], data[1])
				if key == 'gui/screen':
					self.show_gui_screen(data, {})
				if key == 'gui/overlay':
					self.hide_gui_overlay(data)
				if key in self.timeouts:
					del self.timeouts[key]


	def set_consciousness(self, new_state) -> None:
		if new_state in Daemon.CONSCIOUSNESS_VALID:
			old_state = self.cortex['#consciousness']
			self.logger.info("CONSCIOUSNESS state changing from '{}' to '{}'".format(old_state, new_state))
			self.logger.debug("CORTEX before state change = {}".format(self.cortex))
			self.cortex['#consciousness'] = new_state
			for action_name in self.actions.keys():
				signal = {"brain": {"consciousness": new_state}}
				cortex = self.cortex.copy()
				self.actions[action_name].process(signal, cortex)
				if action_name in cortex:
					self.cortex[action_name] = cortex[action_name]
			self.process_queued_signals()
			self.logger.debug("CORTEX after state change  = {}".format(self.cortex))


	def set_system_time(self, datetime_now) -> None:
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
		self.queue_signal("*", {"brain": {"time": datetime_now}})


	def show_gui_screen(self, screen, parameter, timeout: int = None) -> None:
		self.logger.info("GUI: screen '{}' activated (previously '{}')".format(screen, self.cortex['#activity']['video'].screen))
		self.cortex['#activity']['video'] = Activity('gui', screen=screen, overlay=self.cortex['#activity']['video'].overlay)
		if timeout is not None and timeout > 0:
			self.set_timeout(timeout, 'gui/screen', 'idle')
		self.queue_signal("*", {"activity": {"gui": {"screen": {"name": screen, "parameter": parameter}}}})


	def hide_gui_screen(self, screen) -> None:
		self.logger.info("GUI: screen 'idle' activated (previously '{}')".format(screen))
		self.cortex['#activity']['video'] = Activity('gui', screen='idle', overlay=self.cortex['#activity']['video'].overlay)
		if 'gui/screen' in self.timeouts:
			del self.timeouts['gui/screen']
		self.queue_signal("*", {"activity": {"gui": {"screen": {"name": "idle", "parameter": ""}}}})


	def show_gui_overlay(self, overlay, parameter, timeout: int = None) -> None:
		self.logger.info("GUI: overlay '{}' activated (previously '{}')".format(overlay, self.cortex['#activity']['video'].overlay))
		self.cortex['#activity']['video'] = Activity('gui', screen=self.cortex['#activity']['video'].screen, overlay=overlay)
		if timeout is not None and timeout > 0:
			self.set_timeout(timeout, 'gui/overlay', overlay)
		self.queue_signal("*", {"activity": {"gui": {"overlay": {"name": overlay, "parameter": parameter}}}})


	def hide_gui_overlay(self, overlay) -> None:
		self.logger.info("GUI: overlay 'none' activated (previously '{}')".format(overlay))
		self.cortex['#activity']['video'] = Activity('gui', screen=self.cortex['#activity']['video'].screen, overlay='none')
		if 'gui/overlay' in self.timeouts:
			del self.timeouts['gui/overlay']
		self.queue_signal("*", {"activity": {"gui": {"overlay": {"name": "none", "parameter": ""}}}})


	def kalliope_play_audio(self, filename) -> None:
		if self.cortex['#activity']['audio'].module != 'kalliope':
			#TODO:error log
			return
		pass


if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

