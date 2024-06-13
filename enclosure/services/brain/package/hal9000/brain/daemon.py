#!/usr/bin/python3

import os
import sys
import time
import re
import json

from datetime import datetime, date, timedelta, time as timeformat
from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon
from .modules import HAL9000_Module


class Activity(object):
	ATTRIBUTE_NAMES = {'local_names', 'global_names', 'hidden_names', 'callbacks'}

	def __init__(self, module: str='none', **kwargs):
		self.local_names = set()
		self.global_names = set(kwargs.get('global_names', set()))
		self.hidden_names = set(kwargs.get('hidden_names', set()))
		self.callbacks = set()
		self.module = module
		self.global_names.add('module')
		self.hidden_names.update(Activity.ATTRIBUTE_NAMES)
		for name, value in kwargs.items():
			if name not in Activity.ATTRIBUTE_NAMES:
				super().__setattr__(name, value)
	def addCallback(self, callback):
		self.callbacks.add(callback)
	def delCallback(self, callback):
		self.callbacks.remove(callback)
	def __setattr__(self, name, new_value):
		if name in Activity.ATTRIBUTE_NAMES:
			super().__setattr__(name, new_value)
			return
		old_value = None
		if hasattr(self, name) is True:
			old_value = getattr(self, name)
		if old_value != new_value:
			commit_value = True
			for callback in self.callbacks:
				commit_value &= callback(self, name, old_value, new_value)
			if commit_value is True:
				if name in self.global_names:
					for attr in self.local_names:
						if attr not in self.global_names and hasattr(self, attr) is True:
							delattr(self, attr)
					self.local_names = set()
				self.local_names.add(name)
				super().__setattr__(name, new_value)
	def __getattr__(self, name):
		return 'none'
	def __repr__(self):
		result = "{"
		result += f"module='{self.module}'"
		for item, value in self.__dict__.items():
			if item not in self.hidden_names and item != 'module':
				result += f",{item}='{value}'"
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
		self.cortex['#consciousness'] = Daemon.CONSCIOUSNESS_AWAKE
		self.cortex['#activity'] = dict()
		self.cortex['#activity']['video'] = Activity('gui', global_names=['screen', 'overlay'], hidden_names=['signal'])
		self.cortex['#activity']['audio'] = Activity('none', global_names=['source'], hidden_names=['signal'])
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
		self.config['boot-timeout']  = configuration.getint('runlevel', 'boot-timeout', fallback=3)
		self.config['boot-finished-action-name']  = configuration.get('runlevel', 'boot-finished-action-name', fallback=None)
		self.config['boot-finished-signal-data']  = configuration.get('runlevel', 'boot-finished-signal-data', fallback=None)
		self.config['sleep-time']  = configuration.get('brain', 'sleep-time', fallback=None)
		self.config['wakeup-time'] = configuration.get('brain', 'wakeup-time', fallback=None)
		if self.config['sleep-time'] == self.config['wakeup-time']:
			#TODO: error message
			raise ConfigurationError
		self.mqtt.subscribe('hal9000/command/brain/consciousness/state')
		for section_name in configuration.sections():
			module_path = configuration.getstring(section_name, 'module', fallback=None)
			if module_path is not None:
				module_type, module_id = section_name.lower().split(':',1)
				if module_type == 'action':
					Action = self.import_plugin(module_path, 'Action')
					if Action is not None:
						action = Action(module_id, daemon=self)
						action.configure(configuration, section_name, self.cortex)
						self.actions[module_id] = action
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
						self.logger.debug(f"mqtt.subscribe('{mqtt_topic}') for trigger '{trigger_id}'")
						self.mqtt.subscribe(mqtt_topic)
		self.logger.debug(f"CORTEX at startup = {self.cortex}")


	def loop(self) -> None:
		self.set_timeout(1, 'action', ['*', {"brain": {"status": {}}}])
		self.booting_timeout = time.monotonic() + self.config['boot-timeout']
		for module in list(self.triggers.values()) + list(self.actions.values()):
			if module.runlevel(self.cortex) == HAL9000_Module.MODULE_RUNLEVEL_UNKNOWN:
				self.booting_modules[str(module)] = module
		self.set_system_time()
		HAL9000_Daemon.loop(self)

	
	def do_loop(self) -> bool:
		if self.booting_timeout is not None:
			for id in list(self.booting_modules.keys()):
				if self.booting_modules[id].runlevel(self.cortex) != HAL9000_Module.MODULE_RUNLEVEL_UNKNOWN:
					del self.booting_modules[id]
			if time.monotonic() > self.booting_timeout:
				self.booting_timeout = None
				self.logger.critical(f"Startup failed (modules that haven't finished startup: {','.join(self.booting_modules.keys())})")
				for id in self.booting_modules.keys():
					error = self.booting_modules[id].runlevel_error(self.cortex)
					syslog = self.logger.error
					if 'level' in error and hasattr(self.logger, error['level']) is True:
						syslog = getattr(self.logger, error['level'])
					syslog(f"Error #{error['code']} for module '{id}': {error['message']}")
#TODO					if self.config['error-message-translation-file'] is not None:
#TODO						error['message'] = self.translate(error['message'], self.config['error-message-translation-file'])
					self.video_gui_screen_show('error', {"code": error['code'], "message": error['message']})
					if "audio" in error and error["audio"] is not None:
						self.audio_play_file(error["audio"])
				self.logger.critical("=================")
				self.logger.critical("Terminating now!!")
				self.logger.critical("=================")
				sys.exit(1) # TODO exit handling
			if len(self.booting_modules) == 0:
				monotonic_now = time.monotonic()
				self.logger.info(f"STARTUP: {monotonic_now:.2f}")
				self.logger.info(f"Startup completed for all modules ({(monotonic_now-(self.booting_timeout-self.config['boot-timeout'])):.2f} seconds)")
				self.booting_timeout = None
				if 'action' in self.timeouts:
					del self.timeouts['action']
				self.process_signal("*", {"brain": {"ready": True}})
				if self.cortex['#consciousness'] == Daemon.CONSCIOUSNESS_AWAKE:
					action_name = self.config['boot-finished-action-name']
					if action_name in self.actions:
						self.queue_signal(action_name, json.loads(self.config['boot-finished-signal-data']))
#TODO						self.cortex['#activity']['video'].screen = 'idle'
					else:
						self.video_gui_screen_show('idle', {})
		self.process_queued_signals()
		self.process_timeouts()
		return True

	
	def on_mqtt(self, client, userdata, message) -> None:
		HAL9000_Daemon.on_mqtt(self, client, userdata, message)
		if message.topic == 'hal9000/command/brain/consciousness/state':
			consciousness_state = message.payload.decode('utf-8')
			if consciousness_state in Daemon.CONSCIOUSNESS_VALID:
				self.set_consciousness(consciousness_state)
			return
		if self.cortex['#consciousness'] == Daemon.CONSCIOUSNESS_AWAKE or self.booting_timeout is not None:
			if 'mqtt' in self.callbacks and message.topic in self.callbacks['mqtt']:
				self.logger.info(f"SYNAPSES fired: {','.join(str(x).split(':',2)[2] for x in self.callbacks['mqtt'][message.topic])}")
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
						self.logger.debug(f"SIGNAL generated from triggers = {signal}")
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
					self.set_consciousness(key)
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


	def set_consciousness(self, new_state) -> None:
		if new_state in Daemon.CONSCIOUSNESS_VALID:
			old_state = self.cortex['#consciousness']
			if old_state != new_state:
				self.logger.info(f"CONSCIOUSNESS state changing from '{old_state}' to '{new_state}'")
				self.logger.debug(f"CORTEX before state change = {self.cortex}")
				self.cortex['#consciousness'] = new_state
				for action_name in self.actions.keys():
					signal = {"brain": {"consciousness": new_state}}
					self.actions[action_name].process(signal, self.cortex)
				self.process_queued_signals()
				self.logger.debug(f"CORTEX after state change  = {self.cortex}")


	def set_system_time(self) -> None:
		datetime_now = datetime.now()
		datetime_synced = os.path.exists('/run/systemd/timesync/synchronized')
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
		self.queue_signal("*", {"brain": {"time": {"synced": datetime_synced}}})
		if datetime_synced is True:
			self.set_timeout(3600, 'system/time', None)
		else:
			self.set_timeout(60, 'system/time', None)


	def video_gui_screen_show(self, screen, parameter, timeout: int = None) -> None:
		if self.cortex['#consciousness'] != Daemon.CONSCIOUSNESS_AWAKE:
			return
		self.cortex['#activity']['video'].screen = screen
		self.cortex['#activity']['video'].signal = {"activity": {"gui": {"screen": {"name": screen, "parameter": parameter}}}}
		if self.cortex['#activity']['video'].screen == screen:
			self.logger.info(f"GUI: screen '{screen}' activated (previously '{self.cortex['#activity']['video'].screen}')")
			if timeout is not None and timeout > 0:
				self.set_timeout(timeout, 'gui/screen', 'idle')


	def video_gui_screen_hide(self, screen) -> None:
		if self.cortex['#consciousness'] != Daemon.CONSCIOUSNESS_AWAKE:
			return
		self.cortex['#activity']['video'].screen = 'idle'
		self.cortex['#activity']['video'].signal = {"activity": {"gui": {"screen": {"name": "idle", "parameter": ""}}}}
		if self.cortex['#activity']['video'].screen == 'idle':
			self.logger.info(f"GUI: screen 'idle' activated (previously '{screen}')")
			if 'gui/screen' in self.timeouts:
				del self.timeouts['gui/screen']


	def video_gui_overlay_show(self, overlay, parameter, timeout: int = None) -> None:
		if self.cortex['#consciousness'] != Daemon.CONSCIOUSNESS_AWAKE:
			return
		self.cortex['#activity']['video'].overlay = overlay
		self.cortex['#activity']['video'].signal = {"activity": {"gui": {"overlay": {"name": overlay, "parameter": parameter}}}}
		if self.cortex['#activity']['video'].overlay == overlay:
			self.logger.info(f"GUI: overlay '{overlay}' activated (previously '{self.cortex['#activity']['video'].overlay}')")
			if timeout is not None and timeout > 0:
				self.set_timeout(timeout, 'gui/overlay', overlay)


	def video_gui_overlay_hide(self, overlay) -> None:
		if self.cortex['#consciousness'] != Daemon.CONSCIOUSNESS_AWAKE:
			return
		self.cortex['#activity']['video'].overlay = 'none'
		self.cortex['#activity']['video'].signal = {"activity": {"gui": {"overlay": {"name": "none", "parameter": ""}}}}
		if self.cortex['#activity']['video'].overlay == 'none':
			self.logger.info(f"GUI: overlay 'none' activated (previously '{overlay}')")
			if 'gui/overlay' in self.timeouts:
				del self.timeouts['gui/overlay']


	def audio_play_file(self, filename) -> None:
#TODO		if self.cortex['#consciousness'] != Daemon.CONSCIOUSNESS_AWAKE:
#TODO			return
#TODO		if self.cortex['#activity']['audio'].module != 'none':
#TODO			#TODO:error log
#TODO			return
#TODO		self.cortex['#activity']['audio'].module = 'alsa'
#TODO		if self.cortex['#activity']['audio'].module != 'alsa':
#TODO			#TODO:error log
#TODO			return
		pass

if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

