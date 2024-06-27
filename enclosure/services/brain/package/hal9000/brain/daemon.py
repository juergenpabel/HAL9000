import os
import sys
import time
import re
import json
import logging
import logging.config
import signal
import importlib

from paho.mqtt.client import Client as MQTT_Client
from datetime import datetime, date, timedelta, time as timeformat
from configparser import ConfigParser

from .        import HAL9000_Abstract
from .plugin  import HAL9000_Plugin, HAL9000_Plugin_Cortex


class Daemon(HAL9000_Abstract):

	CONSCIOUSNESS_AWAKE = 'awake'
	CONSCIOUSNESS_ASLEEP = 'asleep'
	CONSCIOUSNESS_VALID = [CONSCIOUSNESS_AWAKE, CONSCIOUSNESS_ASLEEP]

	def __init__(self) -> None:
		HAL9000_Abstract.__init__(self, 'brain')
		self.logger = logging.getLogger()
		self.mqtt = None
		self.config = dict()
		self.commands = dict()
		self.loop_exit = False
		self.cortex = dict()
		self.cortex['plugin'] = dict()
		self.cortex['plugin']['brain'] = HAL9000_Plugin_Cortex('brain', valid_names=['consciousness'], state='starting')
		self.actions = dict()
		self.triggers = dict()
		self.bindings = dict()
		self.callbacks = dict()
		self.timeouts = dict()
		self.init_timeout = None
		self.init_plugins = { HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN: {},
		                      HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING: {},
		                      HAL9000_Plugin.PLUGIN_RUNLEVEL_RUNNING: {},
		                      HAL9000_Plugin.PLUGIN_RUNLEVEL_HALTING: {}}
		signal.signal(signal.SIGHUP, self.signal)
		signal.signal(signal.SIGTERM, self.signal)
		signal.signal(signal.SIGQUIT, self.signal)
		signal.signal(signal.SIGINT, self.signal)

	def signal(self, number, frame):
		self.loop_exit = True


	def configure(self, filename: str) -> None:
		logging.config.fileConfig(filename)
		self.logger.info(f"LOADING CONFIGURATION '{filename}'")
		self.logger.info(f"Log-level set to '{logging.getLevelName(self.logger.level)}'")
		self.configuration = ConfigParser(delimiters='=', converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
		                                                         'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
		self.configuration.read(filename)
		self.config['loop-delay-active'] = self.configuration.getfloat('daemon:brain', 'loop-delay-active', fallback=0.01)
		self.config['loop-delay-paused'] = self.configuration.getfloat('daemon:brain', 'loop-delay-paused', fallback=0.10)
		self.config['mqtt-enabled']      = self.configuration.getboolean('daemon:brain', 'mqtt-enabled', fallback=True)
		self.config['mqtt-client']       = self.configuration.getstring('mqtt', 'client', fallback='hal9000-daemon-brain')
		self.config['mqtt-server']       = str(os.getenv('MQTT_SERVER', default=self.configuration.getstring('mqtt', 'server', fallback='127.0.0.1')))
		self.config['mqtt-port']         = int(os.getenv('MQTT_PORT', default=self.configuration.getint('mqtt', 'port', fallback=1883)))
		self.config['mqtt-loop-thread']  = self.configuration.getboolean('mqtt', 'loop-thread', fallback=True)
		self.config['mqtt-loop-timeout'] = self.configuration.getfloat('mqtt', 'loop-timeout', fallback=0.01)
		self.config['mqtt-server'] = str(os.getenv('MQTT_SERVER', default=self.config['mqtt-server']))
		self.config['mqtt-port']   = int(os.getenv('MQTT_PORT',   default=self.config['mqtt-port']))
		if self.config['mqtt-enabled']:
			self.mqtt = MQTT_Client(self.config['mqtt-client'])
			self.mqtt.connect(self.config['mqtt-server'], self.config['mqtt-port'])
			self.mqtt.subscribe('hal9000/command/brain/command')
			self.mqtt.on_message = self.on_mqtt
		self.config['startup:init-timeout'] = self.configuration.getint('startup', 'init-timeout', fallback=5)
		self.config['brain:sleep-time']  = self.configuration.get('brain', 'sleep-time', fallback=None)
		self.config['brain:wakeup-time'] = self.configuration.get('brain', 'wakeup-time', fallback=None)
		self.config['help:error-url'] = self.configuration.getstring('help', 'error-url', fallback=None)
		self.mqtt.subscribe('hal9000/command/brain/consciousness/state')
		for section_name in self.configuration.sections():
			plugin_path = self.configuration.getstring(section_name, 'plugin', fallback=None)
			if plugin_path is not None:
				plugin_type, plugin_id = section_name.lower().split(':',1)
				if plugin_type == 'action':
					Action = self.import_plugin(plugin_path, 'Action')
					if Action is not None:
						plugin_cortex = HAL9000_Plugin_Cortex(plugin_id)
						action = Action(plugin_id, plugin_cortex, daemon=self)
						self.actions[plugin_id] = action
				if plugin_type == 'trigger':
					Trigger = self.import_plugin(plugin_path, 'Trigger')
					if Trigger is not None:
						plugin_cortex = HAL9000_Plugin_Cortex(plugin_id)
						trigger = Trigger(plugin_id, plugin_cortex)
						self.triggers[plugin_id] = trigger
		for section_name in self.configuration.sections():
			plugin_path = self.configuration.getstring(section_name, 'plugin', fallback=None)
			if plugin_path is not None:
				plugin_type, plugin_id = section_name.lower().split(':',1)
				if plugin_type == 'action':
					self.actions[plugin_id].configure(self.configuration, section_name)
				if plugin_type == 'trigger':
					self.triggers[plugin_id].configure(self.configuration, section_name)
		for binding_name in self.configuration.options('bindings'):
			self.bindings[binding_name] = list()
			actions = self.configuration.getlist('bindings', binding_name)
			for action in actions:
				self.bindings[binding_name].append(action)
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
						self.logger.debug(f"MQTT.subscribe('{mqtt_topic}') for trigger '{trigger_id}'")
						self.mqtt.subscribe(mqtt_topic)
		for section_name in self.configuration.sections():
			if section_name.startswith('command:'):
				command_exec = self.configuration.getstring(section_name, 'exec', fallback=None)
				if command_exec is not None:
					command_name = section_name[8:]
					self.commands[command_name] = command_exec


	def import_plugin(self, plugin_name: str, class_name: str) -> HAL9000_Plugin:
		plugin = importlib.import_module(plugin_name)
		if plugin is not None:
			return getattr(plugin, class_name)
		return None


	def loop(self) -> None:
		if self.config['brain:sleep-time'] is None or self.config['brain:wakeup-time'] is None:
			self.cortex['plugin']['brain'].consciousness = Daemon.CONSCIOUSNESS_AWAKE
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
				self.cortex['plugin']['brain'].consciousness = Daemon.CONSCIOUSNESS_AWAKE
			if next_datetime_wakeup < next_datetime_sleep:
				self.cortex['plugin']['brain'].consciousness = Daemon.CONSCIOUSNESS_ASLEEP
		self.init_timeout = time.monotonic() + self.config['startup:init-timeout']
		for plugin in list(self.triggers.values()) + list(self.actions.values()):
			plugin_id = str(plugin)
			plugin_runlevel = plugin.runlevel()
			self.init_plugins[plugin_runlevel][plugin_id] = plugin
		self.logger.info(f"Startup initialized (plugins that need runtime registration):")
		for id, plugin in self.init_plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN].items():
			self.logger.info(f" - Plugin '{id.split(':').pop()}'")
		self.logger.debug(f"CORTEX at startup = {self.cortex}")
		delay_active = self.config['loop-delay-active']
		delay_paused = self.config['loop-delay-paused']
		mqtt_enabled = self.config['mqtt-enabled']
		mqtt_thread  = self.config['mqtt-loop-thread']
		mqtt_timeout = self.config['mqtt-loop-timeout']
		if mqtt_thread is True:
			self.mqtt.loop_start()
			self.mqtt._thread.name = 'MqttThread'
		try:
			while self.do_loop() is True and self.loop_exit is False:
				if mqtt_thread is False:
					self.mqtt.loop(timeout=mqtt_timeout)
				time.sleep(delay_active)
			if self.loop_exit is True:
				self.logger.info("loop() => self.loop_exit==True (probably due to a signal)")
			else:
				self.logger.info("loop() => self.do_loop() returned False (probably due to lack of heartbeat)")
		except:
			raise # TODO
			pass
		if mqtt_thread is True:
			self.mqtt.loop_stop()

	
	def do_loop(self) -> bool:
		for runlevel in [HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN, HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING]:
			if runlevel in self.init_plugins:
				for id, plugin in self.init_plugins[runlevel].items():
					plugin_runlevel = plugin.runlevel()
					if plugin_runlevel != runlevel:
						self.logger.info(f"Plugin '{id.split(':').pop()}' is now in runlevel '{plugin_runlevel}'")
						self.init_plugins[runlevel][id] = None
						self.init_plugins[plugin_runlevel][id] = plugin
				self.init_plugins[runlevel] = {id:plugin for id,plugin in self.init_plugins[runlevel].items() if plugin is not None}
		if self.init_timeout is not None:
			if time.monotonic() > self.init_timeout:
				self.init_timeout = None
				self.logger.critical(f"Startup failed (plugins that haven't reported their runlevel):")
				for id, plugin in self.init_plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN].items():
					error = plugin.runlevel_error()
					self.logger.critical(f"    Plugin '{id.split(':').pop()}': Error #{error['code']} => {error['message']}")
					self.video_gui_screen_show('error', {'code': error['code'], 'message': error['message']})
				self.logger.critical("=================")
				self.logger.critical("Terminating now!!")
				self.logger.critical("=================")
				sys.exit(1) # TODO exit handling
			if len(self.init_plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN]) == 0:
				self.logger.info(f"Startup in progress for all plugins")
				self.init_timeout = None
				if 'action' in self.timeouts:
					del self.timeouts['action']
				del self.init_plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN]
				for plugin in self.cortex['plugin'].values():
					plugin.addNameCallback(self.on_plugin_callback, '*')
		if self.init_timeout is None:
			if HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING in self.init_plugins:
				if len(self.init_plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING]) == 0:
					del self.init_plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING]
					self.logger.info(f"Startup completed for all plugins")
					self.cortex['plugin']['brain'].state = 'ready'
					self.logger.debug(f"CORTEX after startup = {self.cortex}")
		self.process_timeouts()
		return True


	def on_plugin_callback(self, plugin, name, old_value, new_value) -> bool:
		logging.getLogger().info(f"Plugin '{plugin.plugin_id}': {name} changes from '{old_value}' to '{new_value}'")
		if plugin.plugin_id == 'brain' and name == 'consciousness':
			if new_value not in Daemon.CONSCIOUSNESS_VALID:
				return False
#TODO?			if new_value == Daemon.CONSCIOUSNESS_AWAKE:
#TODO?			if new_value == Daemon.CONSCIOUSNESS_ASLEEP:
		return True


	def on_mqtt(self, client, userdata, message) -> None:
		self.logger.debug(f"MQTT received: {message.topic} => {message.payload.decode('utf-8')}")
		if message.topic == 'hal9000/command/brain/consciousness/state':
			consciousness_state = message.payload.decode('utf-8')
			if consciousness_state in Daemon.CONSCIOUSNESS_VALID:
				self.cortex['plugin']['brain'].consciousness = consciousness_state
			return
		if message.topic == 'hal9000/command/brain/command':
			payload = message.payload.decode('utf-8')
			if payload in self.commands:
				self.logger.info(f"Executing configured command with id '{payload}': {self.commands[payload]}")
				os.system(self.commands[payload])
		if self.cortex['plugin']['brain'].consciousness == Daemon.CONSCIOUSNESS_AWAKE or HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING in self.init_plugins:
			if 'mqtt' in self.callbacks and message.topic in self.callbacks['mqtt']:
				self.logger.debug(f"CORTEX before triggers = {self.cortex}")
				self.logger.debug(f"TRIGGERS: {','.join(str(x).split(':',2)[2] for x in self.callbacks['mqtt'][message.topic])}")
				signals = dict()
				for trigger in self.callbacks['mqtt'][message.topic]:
					signal = trigger.handle(message)
					if signal is not None and bool(signal) is not False:
						binding_name = str(trigger).split(':', 2)[2]
						signals[binding_name] = signal
				for binding_name in signals.keys():
					signal = signals[binding_name]
					for plugin_name in signal.keys():
						if plugin_name in self.cortex['plugin']:
							plugin = self.cortex['plugin'][plugin_name]
							self.logger.debug(f"SIGNAL for plugin '{plugin_name}' generated from triggers: '{signal[plugin_name]}'")
							plugin.signal(signal[plugin_name])
							signal = None
				self.logger.debug(f"CORTEX after actions   = {self.cortex}")


	def set_timeout(self, timeout_seconds, timeout_key, timeout_data) -> None:
		self.timeouts[timeout_key] = datetime.now()+timedelta(seconds=timeout_seconds), timeout_data


	def process_timeouts(self) -> None:
		for key in self.timeouts.copy().keys():
			timeout, data = self.timeouts[key]
			if datetime.now() > timeout:
				if key in Daemon.CONSCIOUSNESS_VALID:
					self.cortex['plugin']['brain'].consciousness = key
					self.set_timeout(86400, key, data)
				if key == 'system/time':
					self.set_system_time()
				if key == 'action':
					self.cortex['plugin'][data[0]].signal(data[1]) # TODO:check if works
				if key == 'gui/screen':
					self.video_gui_screen_show(data, {})
				if key == 'gui/overlay':
					self.video_gui_overlay_hide(data)
				if key in self.timeouts:
					if datetime.now() > self.timeouts[key][0]:
						del self.timeouts[key]


	def set_system_time(self) -> None:
		datetime_synced = os.path.exists('/run/systemd/timesync/synchronized')
		self.cortex['plugin']['brain'].signal({'time': {'synced': datetime_synced}})
		if datetime_synced is True:
			self.set_timeout(3600, 'system/time', None)
		else:
			self.set_timeout(60, 'system/time', None)


	def video_gui_screen_show(self, screen, parameter, timeout: int = None) -> None:
		if self.cortex['plugin']['brain'].consciousness != Daemon.CONSCIOUSNESS_AWAKE:
			return
		if timeout is not None and timeout > 0:
			self.set_timeout(timeout, 'gui/screen', 'idle')
		self.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': screen, 'parameter': parameter}}})


	def video_gui_screen_hide(self, screen) -> None:
		if self.cortex['plugin']['brain'].consciousness != Daemon.CONSCIOUSNESS_AWAKE:
			return
		if 'gui/screen' in self.timeouts:
			del self.timeouts['gui/screen']
		self.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'idle', 'parameter': {}}}})


	def video_gui_overlay_show(self, overlay, parameter, timeout: int = None) -> None:
		if self.cortex['plugin']['brain'].consciousness != Daemon.CONSCIOUSNESS_AWAKE:
			return
		if timeout is not None and timeout > 0:
			self.set_timeout(timeout, 'gui/overlay', overlay)
		self.cortex['plugin']['frontend'].signal({'gui': {'overlay': {'name': overlay, 'parameter': parameter}}})


	def video_gui_overlay_hide(self, overlay) -> None:
		if self.cortex['plugin']['brain'].consciousness != Daemon.CONSCIOUSNESS_AWAKE:
			return
		if 'gui/overlay' in self.timeouts:
			del self.timeouts['gui/overlay']
		self.cortex['plugin']['frontend'].signal({'gui': {'overlay': {'name': 'none', 'parameter': {}}}})

