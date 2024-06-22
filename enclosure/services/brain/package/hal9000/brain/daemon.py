#!/usr/bin/python3

import os
import sys
import time
import re
import json
import logging

from datetime import datetime, date, timedelta, time as timeformat
from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon
from .modules import HAL9000_Module


class Service(object):
	ATTRIBUTE_NAMES = {'valid_names', 'hidden_names', 'callbacks'}

	def __init__(self, module: str='none', **kwargs):
		self.valid_names = set(kwargs.get('valid_names', set()))
		self.hidden_names = set(kwargs.get('hidden_names', set()))
		self.callbacks = set()
		self.module = module
		self.valid_names.add('module')
		self.valid_names.add('state')
		self.hidden_names.update(Service.ATTRIBUTE_NAMES)
		for name, value in kwargs.items():
			if name not in Service.ATTRIBUTE_NAMES:
				super().__setattr__(name, value)
	def addCallback(self, callback):
		self.callbacks.add(callback)
	def delCallback(self, callback):
		self.callbacks.remove(callback)
	def __setattr__(self, name, new_value):
		if name in Service.ATTRIBUTE_NAMES:
			super().__setattr__(name, new_value)
			return
		old_value = None
		if hasattr(self, name) is True:
			old_value = getattr(self, name)
		if str(old_value) != str(new_value):
			commit_value = True
			for callback in self.callbacks:
				commit_value &= callback(self, name, old_value, new_value)
			if commit_value is True:
				super().__setattr__(name, new_value)
	def __getattr__(self, name):
		return '<uninitialized>'
	def __repr__(self):
		result = '{'
		result += f'module=\'{self.module}\''
		for item, value in self.__dict__.items():
			if item not in self.hidden_names and item != 'module':
				result += f',{item}=\'{value}\''
		result += '}'
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
		self.cortex['service'] = dict()
		self.cortex['service']['brain'] = Service('brain', valid_names=['consciousness'], hidden_names=['signal'])
		self.cortex['service']['frontend'] = Service('frontend', valid_names=['screen', 'overlay'], hidden_names=['signal'])
		self.cortex['service']['kalliope'] = Service('kalliope', valid_names=['input', 'output', 'volume', 'mute'], hidden_names=['signal'])
		self.actions = dict()
		self.triggers = dict()
		self.synapses = dict()
		self.callbacks = dict()
		self.timeouts = dict()
		self.init_timeout = None
		self.init_modules = { HAL9000_Module.MODULE_RUNLEVEL_UNKNOWN: {},
		                      HAL9000_Module.MODULE_RUNLEVEL_STARTING: {},
		                      HAL9000_Module.MODULE_RUNLEVEL_RUNNING: {},
		                      HAL9000_Module.MODULE_RUNLEVEL_HALTING: {}}
		self.actions_queued = list()


	def configure(self, filename: str) -> None:
		HAL9000_Daemon.configure(self, filename)
		self.config['startup:init-timeout'] = self.configuration.getint('startup', 'init-timeout', fallback=5)
		self.config['brain:sleep-time']  = self.configuration.get('brain', 'sleep-time', fallback=None)
		self.config['brain:wakeup-time'] = self.configuration.get('brain', 'wakeup-time', fallback=None)
		self.config['help:error-url'] = self.configuration.getstring('help', 'error-url', fallback=None)
		self.mqtt.subscribe('hal9000/command/brain/consciousness/state')
		for section_name in self.configuration.sections():
			module_path = self.configuration.getstring(section_name, 'module', fallback=None)
			if module_path is not None:
				module_type, module_id = section_name.lower().split(':',1)
				if module_type == 'action':
					Action = self.import_plugin(module_path, 'Action')
					if Action is not None:
						action = Action(module_id, daemon=self)
						action.configure(self.configuration, section_name, self.cortex)
						self.actions[module_id] = action
				if module_type == 'trigger':
					Trigger = self.import_plugin(module_path, 'Trigger')
					if Trigger is not None:
						trigger = Trigger(module_id)
						trigger.configure(self.configuration, section_name)
						self.triggers[module_id] = trigger
		for synapse_name in self.configuration.options('synapses'):
			self.synapses[synapse_name] = list()
			actions = self.configuration.getlist('synapses', synapse_name)
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
						self.logger.debug(f"mqtt.subscribe('{mqtt_topic}') for trigger '{trigger_id}'")
						self.mqtt.subscribe(mqtt_topic)


	def loop(self) -> None:
		if self.config['brain:sleep-time'] is None or self.config['brain:wakeup-time'] is None:
			self.cortex['service']['brain'].consciousness = Daemon.CONSCIOUSNESS_AWAKE
		else:
			next_datetime_sleep = datetime.combine(date.today(), timeformat.fromisoformat(self.config['brain:sleep-time']))
			if(datetime.now() > next_datetime_sleep):
				next_datetime_sleep += timedelta(hours=24)
			self.timeouts[Daemon.CONSCIOUSNESS_ASLEEP] = next_datetime_sleep, None
			next_datetime_wakeup = datetime.combine(date.today(), timeformat.fromisoformat(self.config['brain:wakeup-time']))
			if(datetime.now() > next_datetime_wakeup):
				next_datetime_wakeup += timedelta(hours=24)
			self.timeouts[Daemon.CONSCIOUSNESS_AWAKE] = next_datetime_wakeup, None
			if next_datetime_sleep < next_datetime_wakeup:
				self.cortex['service']['brain'].consciousness = Daemon.CONSCIOUSNESS_AWAKE
			if next_datetime_wakeup < next_datetime_sleep:
				self.cortex['service']['brain'].consciousness = Daemon.CONSCIOUSNESS_ASLEEP
		self.init_timeout = time.monotonic() + self.config['startup:init-timeout']
		for module in list(self.triggers.values()) + list(self.actions.values()):
			module_id = str(module)
			module_runlevel = module.runlevel(self.cortex)
			self.init_modules[module_runlevel][module_id] = module
		self.logger.info(f"Startup initialized (modules that need runtime registration):")
		for id, module in self.init_modules[HAL9000_Module.MODULE_RUNLEVEL_UNKNOWN].items():
			self.logger.info(f"    Module '{id.split(':').pop()}'")
		self.logger.debug(f"CORTEX at startup = {self.cortex}")
		self.set_timeout(1, 'action', ['*', {'brain': {'status': {}}}])
		HAL9000_Daemon.loop(self)

	
	def do_loop(self) -> bool:
		for runlevel in [HAL9000_Module.MODULE_RUNLEVEL_UNKNOWN, HAL9000_Module.MODULE_RUNLEVEL_STARTING]:
			if runlevel in self.init_modules:
				for id, module in self.init_modules[runlevel].items():
					module_runlevel = module.runlevel(self.cortex)
					if module_runlevel != runlevel:
						self.logger.info(f"Module '{id.split(':').pop()}' is now in runlevel '{module_runlevel}'")
						self.init_modules[runlevel][id] = None
						self.init_modules[module_runlevel][id] = module
				self.init_modules[runlevel] = {id:module for id,module in self.init_modules[runlevel].items() if module is not None}
		if self.init_timeout is not None:
			if time.monotonic() > self.init_timeout:
				self.init_timeout = None
				self.logger.critical(f"Startup failed (modules that haven't reported their runlevel):")
				for id, module in self.init_modules[HAL9000_Module.MODULE_RUNLEVEL_UNKNOWN].items():
					error = module.runlevel_error(self.cortex)
					self.logger.critical(f"    Module '{id.split(':').pop()}': Error #{error['code']} => {error['message']}")
					self.video_gui_screen_show('error', {'code': error['code'], 'message': error['message']})
				self.logger.critical("=================")
				self.logger.critical("Terminating now!!")
				self.logger.critical("=================")
				sys.exit(1) # TODO exit handling
			if len(self.init_modules[HAL9000_Module.MODULE_RUNLEVEL_UNKNOWN]) == 0:
				self.logger.info(f"Startup in progress for all modules")
				self.init_timeout = None
				if 'action' in self.timeouts:
					del self.timeouts['action']
				del self.init_modules[HAL9000_Module.MODULE_RUNLEVEL_UNKNOWN]
				for module in self.cortex['service'].values():
					module.addCallback(self.on_module_activity)
		if self.init_timeout is None:
			if HAL9000_Module.MODULE_RUNLEVEL_STARTING in self.init_modules:
				if len(self.init_modules[HAL9000_Module.MODULE_RUNLEVEL_STARTING]) == 0:
					del self.init_modules[HAL9000_Module.MODULE_RUNLEVEL_STARTING]
					self.logger.info(f"Startup completed for all modules")
					self.process_signal('*', {'brain': {'ready': True}})
					self.logger.debug(f"CORTEX after startup = {self.cortex}")
		self.process_queued_signals()
		self.process_timeouts()
		return True


	def on_module_activity(self, module, name, old_value, new_value) -> bool:
		if name not in module.hidden_names:
			logging.getLogger().info(f"Module '{module.module}': {name} changes from '{old_value}' to '{new_value}'")
		if module.module == 'brain' and name == 'consciousness':
			if new_value not in Daemon.CONSCIOUSNESS_VALID:
				return False
			for action_name in self.actions.keys():
				signal = {'brain': {'consciousness': new_value}}
				self.actions[action_name].process(signal, self.cortex)
			self.process_queued_signals()
		return True


	def on_mqtt(self, client, userdata, message) -> None:
		HAL9000_Daemon.on_mqtt(self, client, userdata, message)
		if message.topic == 'hal9000/command/brain/consciousness/state':
			consciousness_state = message.payload.decode('utf-8')
			if consciousness_state in Daemon.CONSCIOUSNESS_VALID:
				self.cortex['service']['brain'].consciousness = consciousness_state
			return
		if message.topic == 'hal9000/command/brain/command':
			payload = message.payload.decode('utf-8')
			if payload in self.commands:
				self.logger.info(f"executing configured command with id '{payload}': {self.commands[payload]}")
				os.system(self.commands[payload])
		if self.cortex['service']['brain'].consciousness == Daemon.CONSCIOUSNESS_AWAKE or HAL9000_Module.MODULE_RUNLEVEL_STARTING in self.init_modules:
			if 'mqtt' in self.callbacks and message.topic in self.callbacks['mqtt']:
				self.logger.debug(f"SYNAPSES fired: {','.join(str(x).split(':',2)[2] for x in self.callbacks['mqtt'][message.topic])}")
				self.logger.debug(f"CORTEX before triggers = {self.cortex}")
				signals = dict()
				for trigger in self.callbacks['mqtt'][message.topic]:
					signal = trigger.handle(message)
					if signal is not None:
						synapse_name = str(trigger).split(':', 2)[2]
						signals[synapse_name] = signal
				for synapse_name in signals.keys():
					signal = signals[synapse_name]
					if signal is not None and bool(signal) is not False:
						self.logger.debug(f"SIGNAL generated from triggers: '{signal}'")
						for action_name in self.synapses[synapse_name]:
							self.actions[action_name].process(signal, self.cortex)
				self.logger.debug(f"CORTEX after actions   = {self.cortex}")
				self.process_queued_signals()


	def process_signal(self, action_name, signal_data) -> None:
		self.logger.debug(f"CORTEX before signal = {self.cortex}")
		action_handlers = []
		if action_name == '*':
			action_handlers = self.actions.keys()
		else:
			action_handlers.append(action_name)
		for action_handler in action_handlers:
			if action_handler in self.actions:
				self.actions[action_handler].process(signal_data, self.cortex)
		self.logger.debug(f"CORTEX after  signal = {self.cortex}")


	def queue_signal(self, action_name, signal_data) -> None:
		self.actions_queued.append([action_name, signal_data])


	def process_queued_signals(self) -> None:
		actions_queued = self.actions_queued.copy()
		self.actions_queued.clear()
		if len(actions_queued) > 0:
			self.logger.debug(f"CORTEX before (postponed) signals = {self.cortex}")
			for action_name, signal_data in actions_queued:
				self.logger.debug(f"Processing (postponed) signal '{signal_data}'")
				action_handlers = []
				if action_name == '*':
					action_handlers = self.actions.keys()
				else:
					action_handlers.append(action_name)
				for action_handler in action_handlers:
					if action_handler in self.actions:
						self.actions[action_handler].process(signal_data, self.cortex)
			self.logger.debug(f"CORTEX after  (postponed) signals = {self.cortex}")


	def set_timeout(self, timeout_seconds, timeout_key, timeout_data) -> None:
		self.timeouts[timeout_key] = datetime.now()+timedelta(seconds=timeout_seconds), timeout_data


	def process_timeouts(self) -> None:
		for key in self.timeouts.copy().keys():
			timeout, data = self.timeouts[key]
			if datetime.now() > timeout:
				if key in Daemon.CONSCIOUSNESS_VALID:
					self.cortex['service']['brain'].consciousness = key
					self.set_timeout(86400, key, data)
				if key == 'system/time':
					self.set_system_time()
				if key == 'action':
					self.queue_signal(data[0], data[1])
				if key == 'gui/screen':
					self.video_gui_screen_show(data, {})
				if key == 'gui/overlay':
					self.video_gui_overlay_hide(data)
				if key in self.timeouts:
					if datetime.now() > self.timeouts[key][0]:
						del self.timeouts[key]


	def set_system_time(self) -> None:
		datetime_synced = os.path.exists('/run/systemd/timesync/synchronized')
		self.queue_signal('*', {'brain': {'time': {'synced': datetime_synced}}})
		if datetime_synced is True:
			self.set_timeout(3600, 'system/time', None)
		else:
			self.set_timeout(60, 'system/time', None)


	def video_gui_screen_show(self, screen, parameter, timeout: int = None) -> None:
		if self.cortex['service']['brain'].consciousness != Daemon.CONSCIOUSNESS_AWAKE:
			return
		if timeout is not None and timeout > 0:
			self.set_timeout(timeout, 'gui/screen', 'idle')
		self.cortex['service']['frontend'].screen = screen
		self.cortex['service']['frontend'].signal = {'signal': {'gui': {'screen': {'name': screen, 'parameter': parameter}}}}


	def video_gui_screen_hide(self, screen) -> None:
		if self.cortex['service']['brain'].consciousness != Daemon.CONSCIOUSNESS_AWAKE:
			return
		if 'gui/screen' in self.timeouts:
			del self.timeouts['gui/screen']
		self.cortex['service']['frontend'].screen = 'idle'
		self.cortex['service']['frontend'].signal = {'signal': {'gui': {'screen': {'name': 'idle', 'parameter': ''}}}}


	def video_gui_overlay_show(self, overlay, parameter, timeout: int = None) -> None:
		if self.cortex['service']['brain'].consciousness != Daemon.CONSCIOUSNESS_AWAKE:
			return
		if timeout is not None and timeout > 0:
			self.set_timeout(timeout, 'gui/overlay', overlay)
		self.cortex['service']['frontend'].overlay = overlay
		self.cortex['service']['frontend'].signal = {'signal': {'gui': {'overlay': {'name': overlay, 'parameter': parameter}}}}


	def video_gui_overlay_hide(self, overlay) -> None:
		if self.cortex['service']['brain'].consciousness != Daemon.CONSCIOUSNESS_AWAKE:
			return
		if 'gui/overlay' in self.timeouts:
			del self.timeouts['gui/overlay']
		self.cortex['service']['frontend'].overlay = 'none'
		self.cortex['service']['frontend'].signal = {'signal': {'gui': {'overlay': {'name': 'none', 'parameter': ''}}}}

