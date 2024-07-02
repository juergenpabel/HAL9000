from os import getenv as os_getenv, \
               system as os_system
from os.path import exists as os_path_exists
from time import monotonic as time_monotonic, \
                 sleep as time_sleep
from logging import getLogger as logging_getLogger, \
                    getLevelName as logging_getLevelName
from signal import signal as signal_signal, \
                   SIGHUP as signal_SIGHUP, \
                   SIGTERM as signal_SIGTERM, \
                   SIGQUIT as signal_SIGQUIT, \
                   SIGINT as signal_SIGINT
from logging.config import fileConfig as logging_config_fileConfig
from importlib import import_module as importlib_import_module

from json import dumps as json_dumps
from asyncio import create_task as asyncio_create_task, \
                    gather as asyncio_gather, \
                    sleep as asyncio_sleep, \
                    Queue as asyncio_Queue, \
                    CancelledError as asyncio_CancelledError
from aiomqtt import Client as aiomqtt_Client, \
                    MqttError as aiomqtt_MqttError
from datetime import datetime as datetime_datetime, \
                     date as datetime_date, \
                     timedelta as datetime_timedelta, \
                     time as datetime_time
from configparser import ConfigParser as configparser_ConfigParser
from dbus_fast.aio import MessageBus
from dbus_fast.auth import AuthExternal, UID_NOT_SPECIFIED
from dbus_fast.constants import BusType


from .plugin import HAL9000_Plugin, HAL9000_Plugin_Cortex


class Daemon(object):

	BRAIN_STATE_STARTING = 'starting'
	BRAIN_STATE_READY = 'ready'
	BRAIN_STATE_AWAKE = 'awake'
	BRAIN_STATE_ASLEEP = 'asleep'
	BRAIN_STATE_DYING = 'dying'
	BRAIN_STATE_VALID = [BRAIN_STATE_STARTING, BRAIN_STATE_READY, BRAIN_STATE_AWAKE, BRAIN_STATE_ASLEEP, BRAIN_STATE_DYING]

	def __init__(self) -> None:
		self.logger = logging_getLogger()
		self.config = {}
		self.commands = {}
		self.tasks = {}
		self.cortex = {'plugin': {'brain': HAL9000_Plugin_Cortex('brain', state='starting')}}
		self.cortex['plugin']['brain'].addNameCallback(self.on_brain_state_callback, 'state')
		self.cortex['plugin']['brain'].addSignalHandler(self.on_brain_signal)
		self.actions = {}
		self.triggers = {}
		self.bindings = {}
		self.callbacks = {'mqtt': {}}
		self.startup_timeout = None
		self.plugins = { HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN: {},
		                 HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING: {},
		                 HAL9000_Plugin.PLUGIN_RUNLEVEL_RUNNING: {},
		                 HAL9000_Plugin.PLUGIN_RUNLEVEL_HALTING: {}}
		signal_signal(signal_SIGHUP, self.on_posix_signal)
		signal_signal(signal_SIGTERM, self.on_posix_signal)
		signal_signal(signal_SIGQUIT, self.on_posix_signal)
		signal_signal(signal_SIGINT, self.on_posix_signal)
		self.signal_queue = asyncio_Queue()
		self.timeout_queue = asyncio_Queue()
		self.mqtt_publish_queue = asyncio_Queue()


	def configure(self, filename: str) -> None:
		logging_config_fileConfig(filename)
		self.logger.info(f"LOADING CONFIGURATION '{filename}'")
		self.logger.info(f"Log-level set to '{logging_getLevelName(self.logger.level)}'")
		self.configuration = configparser_ConfigParser(delimiters='=',
		                                               converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
		                                                           'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
		self.configuration.read(filename)
		self.config['mqtt:server']       = str(os_getenv('MQTT_SERVER', default=self.configuration.getstring('mqtt', 'server', fallback='127.0.0.1')))
		self.config['mqtt:port']         = int(os_getenv('MQTT_PORT', default=self.configuration.getint('mqtt', 'port', fallback=1883)))
		self.config['startup:init-timeout'] = self.configuration.getint('startup', 'init-timeout', fallback=5)
		self.config['brain:sleep-time']  = self.configuration.get('brain', 'sleep-time', fallback=None)
		self.config['brain:wakeup-time'] = self.configuration.get('brain', 'wakeup-time', fallback=None)
		self.config['help:error-url'] = self.configuration.getstring('help', 'error-url', fallback=None)
		for section_name in self.configuration.sections():
			plugin_path = self.configuration.getstring(section_name, 'plugin', fallback=None)
			if plugin_path is not None:
				module = importlib_import_module(plugin_path)
				if module is not None:
					plugin_type, plugin_id = section_name.lower().split(':',1)
					match plugin_type.lower():
						case 'action':
							Action = getattr(module, 'Action')
							if Action is not None:
								plugin_cortex = HAL9000_Plugin_Cortex(plugin_id)
								action = Action(plugin_id, plugin_cortex, daemon=self)
								self.actions[plugin_id] = action
						case 'trigger':
							Trigger = getattr(module, 'Trigger')
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
						if mqtt_topic not in self.callbacks['mqtt']:
							self.callbacks['mqtt'][mqtt_topic] = list()
						self.callbacks['mqtt'][mqtt_topic].append(trigger)
		for section_name in self.configuration.sections():
			if section_name.startswith('command:'):
				command_exec = self.configuration.getstring(section_name, 'exec', fallback=None)
				if command_exec is not None:
					command_name = section_name[8:]
					self.commands[command_name] = command_exec


	async def loop(self):
		results = {'main': None}
		try:
			self.startup_timeout = time_monotonic() + self.config['startup:init-timeout']
			for plugin in list(self.triggers.values()) + list(self.actions.values()):
				plugin_id = str(plugin)
				plugin_runlevel = plugin.runlevel()
				self.plugins[plugin_runlevel][plugin_id] = plugin
			self.logger.info(f"Startup initialized (plugins that need runtime registration):")
			for id, plugin in self.plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN].items():
				self.logger.info(f" - Plugin '{id.split(':').pop()}'")
			self.tasks['signals'] = asyncio_create_task(self.task_signal())
			self.tasks['timeouts'] = asyncio_create_task(self.task_timeouts())
			self.tasks['mqtt'] = asyncio_create_task(self.task_mqtt())
			self.logger.debug(f"CORTEX at startup = {self.cortex}")
			while self.cortex['plugin']['brain'].state != Daemon.BRAIN_STATE_DYING:
				await asyncio_sleep(0.001)
				for runlevel in [HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN, HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING]:
					if runlevel in self.plugins:
						for id, plugin in self.plugins[runlevel].items():
							plugin_runlevel = plugin.runlevel()
							if plugin_runlevel != runlevel:
								self.logger.info(f"Plugin '{id.split(':').pop()}' is now in runlevel '{plugin_runlevel}'")
								self.plugins[runlevel][id] = None
								self.plugins[plugin_runlevel][id] = plugin
						self.plugins[runlevel] = {id:plugin for id,plugin in self.plugins[runlevel].items() if plugin is not None}
				if self.startup_timeout is not None:
					if time_monotonic() > self.startup_timeout:
						self.logger.critical(f"Startup failed (plugins that haven't reported their runlevel):")
						for id, plugin in self.plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN].items():
							error = plugin.runlevel_error()
							self.logger.critical(f"    Plugin '{id.split(':').pop()}': Error #{error['code']} => {error['message']}")
							self.add_signal('frontend', {'gui': {'screen': {'name': 'error',
							                                                'parameter': {'code': error['code'], 'message': error['message']}}}})
						self.logger.critical("Terminating due to plugins that haven't reached runlevel 'starting' within timelimit")
						self.cortex['plugin']['brain'].state = Daemon.BRAIN_STATE_DYING
					if len(self.plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN]) == 0:
						self.logger.info(f"Startup in progress for all plugins")
						self.startup_timeout = None
						del self.plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN]
						for plugin in self.cortex['plugin'].values():
							plugin.addNameCallback(self.on_plugin_callback, '*')
				if self.startup_timeout is None:
					if HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING in self.plugins:
						if len(self.plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING]) == 0:
							del self.plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING]
							self.logger.info(f"Startup completed for all plugins")
							self.cortex['plugin']['brain'].state = Daemon.BRAIN_STATE_READY
							self.logger.debug(f"CORTEX after startup = {self.cortex}")
		except Exception as e:
			self.cortex['plugin']['brain'].state = Daemon.BRAIN_STATE_DYING
			results['main'] = e
		for name, task in self.tasks.items():
			task.cancel()
			results[name] = (await asyncio_gather(task, return_exceptions=True)).pop()
		return results
			

	async def task_mqtt_command_listener(self, mqtt):
		try:
			async for message in mqtt.messages:
				topic = message.topic.value
				payload = message.payload.decode('utf-8')
				self.logger.debug(f"MQTT received: {topic} => {str(chr(0x27))+str(chr(0x27)) if payload == '' else payload}")
				match topic:
					case 'hal9000/command/brain/exit':
						self.cortex['plugin']['brain'].state = Daemon.BRAIN_STATE_DYING
					case 'hal9000/command/brain/state':
						if self.cortex['plugin']['brain'].state in [Daemon.BRAIN_STATE_AWAKE, Daemon.BRAIN_STATE_ASLEEP]:
							if payload in [Daemon.BRAIN_STATE_AWAKE, Daemon.BRAIN_STATE_ASLEEP]:
								self.cortex['plugin']['brain'].state = payload
					case 'hal9000/command/brain/command':
						if payload in self.commands:
							self.logger.info(f"Executing configured command with id '{payload}': {self.commands[payload]}")
							os_system(self.commands[payload])
					case _:
						if self.cortex['plugin']['brain'].state in [Daemon.BRAIN_STATE_STARTING, Daemon.BRAIN_STATE_READY, Daemon.BRAIN_STATE_AWAKE]:
							if topic in self.callbacks['mqtt']:
								self.logger.debug(f"TRIGGERS: {','.join(str(x).split(':',2)[2] for x in self.callbacks['mqtt'][topic])}")
								self.logger.debug(f"CORTEX before triggers = {self.cortex}")
								signals = {}
								for trigger in self.callbacks['mqtt'][topic]:
									signal = trigger.handle(message)
									if signal is not None and bool(signal) is not False:
										binding_name = str(trigger).split(':', 2)[2]
										signals[binding_name] = signal
								for binding_name in signals.keys():
									signal = signals[binding_name]
									for plugin_name in signal.keys():
										if plugin_name in self.cortex['plugin']:
											plugin = self.cortex['plugin'][plugin_name]
											signal = signal[plugin_name]
											self.logger.debug(f"SIGNAL for plugin '{plugin_name}' generated from triggers: '{signal}'")
											await plugin.signal(signal)
								self.logger.debug(f"CORTEX after signals   = {self.cortex}")
		except aiomqtt_MqttError as e:
			if self.tasks['mqtt'].cancelled() is False and self.cortex['plugin']['brain'].state != Daemon.BRAIN_STATE_DYING:
				raise e
		except asyncio_CancelledError as e:
			pass


	async def task_mqtt_event_listener(self, mqtt):
		try:
			while self.cortex['plugin']['brain'].state != Daemon.BRAIN_STATE_DYING:
				if self.mqtt_publish_queue.empty() is False:
					data = await self.mqtt_publish_queue.get()
					if isinstance(data, dict) is True and 'topic' in data and 'payload' in data:
						topic = data['topic']
						payload = data['payload']
						if isinstance(payload, dict) is True:
							payload = json_dumps(payload)
						await mqtt.publish(topic, payload)
						self.logger.debug(f"MQTT published: {topic} => {str(chr(0x27))+str(chr(0x27)) if payload == '' else payload}")
				await asyncio_sleep(0.01)
		except asyncio_CancelledError as e:
			pass


	async def task_mqtt(self):
		task_events = None
		task_commands = None
		try:
			async with aiomqtt_Client(self.config['mqtt:server'], self.config['mqtt:port'], identifier='hal9000-brain') as mqtt:
				task_events = asyncio_create_task(self.task_mqtt_event_listener(mqtt))
				task_commands = asyncio_create_task(self.task_mqtt_command_listener(mqtt))
				await mqtt.subscribe('hal9000/command/brain/exit')
				self.logger.debug(f"MQTT.subscribe('hal9000/command/brain/state') for plugin 'brain'")
				await mqtt.subscribe('hal9000/command/brain/state')
				self.logger.debug(f"MQTT.subscribe('hal9000/command/brain/command') for plugin 'brain'")
				await mqtt.subscribe('hal9000/command/brain/command')
				for mqtt_topic, trigger in self.callbacks['mqtt'].items():
					self.logger.debug(f"MQTT.subscribe('{mqtt_topic}') for trigger '{str(trigger)}'")
					await mqtt.subscribe(mqtt_topic)
				while self.cortex['plugin']['brain'].state != Daemon.BRAIN_STATE_DYING:
					await asyncio_sleep(0.01)
				task_events.cancel()
				task_commands.cancel()
				await asyncio_gather(task_events, task_commands)
		except asyncio_CancelledError as e:
			if task_events is not None:
				task_events.cancel()
				await asyncio_gather(task_events)
			if task_commands is not None:
				task_commands.cancel()
				await asyncio_gather(task_commands)
			self.mqtt_publish_queue = None
		except Exception as e:
			self.logger.critical(f"Daemon.task_mqtt(): {str(e)}")
			self.cortex['plugin']['brain'].state = Daemon.BRAIN_STATE_DYING
			raise e


	async def task_signal(self):
		try:
			while self.cortex['plugin']['brain'].state != Daemon.BRAIN_STATE_DYING:
				if self.signal_queue.empty() is False:
					data = await self.signal_queue.get()
					if isinstance(data, dict) is True and 'plugin' in data and 'signal' in data:
						plugin = data['plugin']
						signal = data['signal']
						self.logger.debug(f"SIGNAL for plugin '{plugin}' generated by Daemon.task_signal(): '{signal}'")
						if plugin in self.cortex['plugin']:
							plugin = self.cortex['plugin'][plugin]
							await plugin.signal(signal)
						else:
							self.logger.warning(f"Ignoring SIGNAL for unknown plugin '{plugin}' - ignoring it (=> BUG)")
					else:
						self.logger.warning(f"Ignoring invalid SIGNAL '{str(signal)}' from signal_queue")
				await asyncio_sleep(0.01)
		except asyncio_CancelledError as e:
			self.signal_queue = None
		except Exception as e:
			self.logger.critical(f"Daemon.task_signal(): {str(e)}")
			self.cortex['plugin']['brain'].state = Daemon.BRAIN_STATE_DYING
			raise e


	async def task_timeouts(self):
		try:
			timeouts = {}
			while self.cortex['plugin']['brain'].state != Daemon.BRAIN_STATE_DYING:
				if self.timeout_queue.empty() is False:
					timeout = await self.timeout_queue.get()
					if isinstance(timeout, dict) is True:
						if 'timestamp' in timeout and 'key' in timeout and 'data' in timeout:
							key = timeout['key']
							if timeout['timestamp'] is not None:
								timeouts[key] = timeout
							else:
								if key in timeouts:
									del timeouts[key]
				await asyncio_sleep(0.01)
				for key, timeout in timeouts.copy().items():
					if datetime_datetime.now().timestamp() > timeout['timestamp']:
						del timeouts[key]
						match key:
							case 'plugin:signal':
								if isinstance(timeout['data'], dict) is True:
									data = timeout['data']
									if 'plugin' in data and 'signal' in data:
										plugin = data['plugin']
										signal = data['signal']
										if isinstance(plugin, str) is True:
											if plugin in self.cortex['plugin']:
												plugin = self.cortex['plugin'][plugin]
											else:
												self.logger.error(f"Unknown plugin '{plugin}' for signal: {signal}")
										if isinstance(plugin, HAL9000_Plugin_Cortex) is True:
											if isinstance(signal, dict) is True:
												await plugin.signal(signal)
							case 'frontend:gui/screen':
								if isinstance(timeout['data'], dict) is True:
									data = timeout['data']
									if 'name' in data and 'parameter' in data:
										self.add_signal('frontend', {'gui': {'screen': {'name': data['name'],
										                                                'parameter': data['parameter']}}})
							case 'frontend:gui/overlay':
								if isinstance(timeout['data'], dict) is True:
									data = timeout['data']
									if 'name' in data and 'parameter' in data:
										self.add_signal('frontend', {'gui': {'overlay': {'name': data['name'],
										                                                 'parameter': data['parameter']}}})
				await asyncio_sleep(0.01)
		except asyncio_CancelledError as e:
			self.timeout_queue = None
		except Exception as e:
			self.logger.critical(f"Daemon.task_timeouts(): {str(e)}")
			import traceback
			traceback.print_tb(e.__traceback__)
			self.cortex['plugin']['brain'].state = Daemon.BRAIN_STATE_DYING
			raise e


	def import_plugin(self, plugin_name: str, class_name: str) -> HAL9000_Plugin:
		plugin = importlib_import_module(plugin_name)
		if plugin is not None:
			return getattr(plugin, class_name)
		return None


	def on_plugin_callback(self, plugin, name, old_value, new_value) -> bool:
		logging_getLogger().info(f"Plugin '{plugin.plugin_id}': {name} changes from '{old_value}' to '{new_value}'")
		if plugin.plugin_id == 'brain' and name == 'state':
			if new_value not in Daemon.BRAIN_STATE_VALID:
				return False
		return True


	def on_brain_state_callback(self, plugin, name, old_state, new_state) -> bool:
		if new_state == Daemon.BRAIN_STATE_READY:
			next_brain_state = Daemon.BRAIN_STATE_AWAKE
			if self.config['brain:sleep-time'] is not None and self.config['brain:wakeup-time'] is not None:
				next_datetime_sleep = datetime_datetime.combine(datetime_date.today(),
				                                                datetime_time.fromisoformat(self.config['brain:sleep-time']))
				if(datetime_datetime.now() > next_datetime_sleep):
					next_datetime_sleep += datetime_timedelta(hours=24)
				self.timeout_queue.put_nowait({'timestamp': next_datetime_sleep.timestamp()-datetime_datetime.now().timestamp(),
				                               'key': Daemon.BRAIN_STATE_ASLEEP, 'data': None})
				next_datetime_wakeup = datetime_datetime.combine(datetime_date.today(),
				                                                 datetime_time.fromisoformat(self.config['brain:wakeup-time']))
				if(datetime_datetime.now() > next_datetime_wakeup):
					next_datetime_wakeup += datetime_timedelta(hours=24)
				self.timeout_queue.put_nowait({'timestamp': next_datetime_wakeup.timestamp()-datetime_datetime.now().timestamp(),
				                               'key': Daemon.BRAIN_STATE_AWAKE, 'data': None})
				if next_datetime_wakeup < next_datetime_sleep:
					next_brain_state = Daemon.BRAIN_STATE_ASLEEP
			self.add_signal('brain', {'state': next_brain_state})
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin_Cortex, signal: dict) -> None:
		if 'state' in signal:
			match self.cortex['plugin']['brain'].state:
				case Daemon.BRAIN_STATE_STARTING:
					if signal['state'] == Daemon.BRAIN_STATE_READY:
						self.cortex['plugin']['brain'].state = signal['state']
				case Daemon.BRAIN_STATE_READY:
					if signal['state'] in [Daemon.BRAIN_STATE_AWAKE, Daemon.BRAIN_STATE_ASLEEP]:
						self.cortex['plugin']['brain'].state = signal['state']
				case Daemon.BRAIN_STATE_AWAKE:
					if signal['state'] in [Daemon.BRAIN_STATE_ASLEEP, Daemon.BRAIN_STATE_DYING]:
						self.cortex['plugin']['brain'].state = signal['state']
					if 'interval' in signal:
						self.add_timeout(signal['interval'], 'plugin:signal', {'plugin': 'brain',
						                                                       'signal': {'state': Daemon.BRAIN_STATE_AWAKE,
						                                                                  'interval': signal['interval']}})
				case Daemon.BRAIN_STATE_ASLEEP:
					if signal['state'] in [Daemon.BRAIN_STATE_AWAKE, Daemon.BRAIN_STATE_DYING]:
						self.cortex['plugin']['brain'].state = signal['state']
					if 'interval' in signal:
						self.add_timeout(signal['interval'], 'plugin:signal', {'plugin': 'brain',
						                                                       'signal': {'state': Daemon.BRAIN_STATE_ASLEEP,
						                                                                  'interval': signal['interval']}})
				case Daemon.BRAIN_STATE_DYING:
					pass


	async def signal(self, plugin: str, signal: dict) -> None:
		if plugin in self.cortex['plugin']:
			await self.cortex['plugin'][plugin].signal(signal)


	def add_signal(self, plugin: str, signal: dict) -> None:
		self.signal_queue.put_nowait({'plugin': plugin, 'signal': signal})


	def add_timeout(self, timeout_seconds: int, timeout_key: str, timeout_data) -> None:
		self.timeout_queue.put_nowait({'timestamp': None if timeout_seconds is None else datetime_datetime.now().timestamp()+timeout_seconds,
		                               'key': timeout_key,
		                               'data': timeout_data})


	def del_timeout(self, timeout_key) -> None:
		self.timeout_queue.put_nowait({'timestamp': None, 'key': timeout_key, 'data': None})


	async def get_system_ipv4(self) -> str:
		bus = await MessageBus(None, BusType.SYSTEM, AuthExternal(UID_NOT_SPECIFIED)).connect()
		introspection = await bus.introspect('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager')
		obj = bus.get_proxy_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager', introspection)
		nm = obj.get_interface('org.freedesktop.NetworkManager')
		for connection in await nm.get_active_connections():
			introspection2 = await bus.introspect('org.freedesktop.NetworkManager', connection)
			obj2 = bus.get_proxy_object('org.freedesktop.NetworkManager', connection, introspection2)
			conf = obj2.get_interface('org.freedesktop.NetworkManager.Connection.Active')
			if await conf.get_default() is True:
				ip4config = await conf.get_ip4_config()
				introspection3 = await bus.introspect('org.freedesktop.NetworkManager', ip4config)
				obj3 = bus.get_proxy_object('org.freedesktop.NetworkManager', ip4config, introspection3)
				data= obj3.get_interface('org.freedesktop.NetworkManager.IP4Config')
				address_data = await data.get_address_data()
				return address_data[0]['address'].value
		return '127.0.0.1'


	def on_posix_signal(self, number, frame):
		self.cortex['plugin']['brain'].state = Daemon.BRAIN_STATE_DYING

