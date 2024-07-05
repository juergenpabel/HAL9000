from os import getenv as os_getenv, \
               system as os_system
from os.path import exists as os_path_exists
from time import monotonic as time_monotonic, \
                 sleep as time_sleep
from datetime import datetime as datetime_datetime, \
                     date as datetime_date, \
                     timedelta as datetime_timedelta, \
                     time as datetime_time
from json import dumps as json_dumps
from logging import getLogger as logging_getLogger, \
                    getLevelName as logging_getLevelName
from logging.config import fileConfig as logging_config_fileConfig
from configparser import ConfigParser as configparser_ConfigParser
from importlib import import_module as importlib_import_module
from signal import signal as signal_signal, \
                   SIGHUP as signal_SIGHUP, \
                   SIGTERM as signal_SIGTERM, \
                   SIGQUIT as signal_SIGQUIT, \
                   SIGINT as signal_SIGINT
from asyncio import create_task as asyncio_create_task, \
                    gather as asyncio_gather, \
                    sleep as asyncio_sleep, \
                    Queue as asyncio_Queue, \
                    CancelledError as asyncio_CancelledError

from aiomqtt import Client as aiomqtt_Client, \
                    MqttError as aiomqtt_MqttError
from apscheduler.schedulers.asyncio import AsyncIOScheduler as apscheduler_schedulers_AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger as apscheduler_triggers_cron_CronTrigger
from apscheduler.triggers.date import DateTrigger as apscheduler_triggers_date_DateTrigger
from dbus_fast.aio import MessageBus
from dbus_fast.auth import AuthExternal, UID_NOT_SPECIFIED
from dbus_fast.constants import BusType


from .plugin import HAL9000_Plugin, HAL9000_Plugin_Status


class Daemon(object):

	BRAIN_STATUS_STARTING = 'starting'
	BRAIN_STATUS_READY = 'ready'
	BRAIN_STATUS_AWAKE = 'awake'
	BRAIN_STATUS_ASLEEP = 'asleep'
	BRAIN_STATUS_DYING = 'dying'

	def __init__(self) -> None:
		self.logger = logging_getLogger()
		self.config = {}
		self.plugins = {}
		self.plugins['brain'] = HAL9000_Plugin_Status('brain', status='starting')
		self.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.plugins['brain'].addSignalHandler(self.on_brain_signal)
		self.tasks = {}
		self.actions = {}
		self.triggers = {}
		self.callbacks = {'mqtt': {}}
		self.scripts = {}
		self.signal_queue = asyncio_Queue()
		self.mqtt_publish_queue = asyncio_Queue()
		self.scheduler = apscheduler_schedulers_AsyncIOScheduler()
		signal_signal(signal_SIGHUP, self.on_posix_signal)
		signal_signal(signal_SIGTERM, self.on_posix_signal)
		signal_signal(signal_SIGQUIT, self.on_posix_signal)
		signal_signal(signal_SIGINT, self.on_posix_signal)


	def configure(self, filename: str) -> None:
		logging_config_fileConfig(filename)
		logging_getLogger('apscheduler').setLevel('WARNING')
		self.logger.info(f"LOADING CONFIGURATION '{filename}'")
		self.logger.info(f"Log-level set to '{logging_getLevelName(self.logger.level)}'")
		self.configuration = configparser_ConfigParser(delimiters='=',
		                                               converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
		                                                           'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
		self.configuration.read(filename)
		self.config['startup:init-timeout'] = self.configuration.getint('startup', 'init-timeout', fallback=10)
		self.config['mqtt:server']       = str(os_getenv('MQTT_SERVER', default=self.configuration.getstring('mqtt', 'server', fallback='127.0.0.1')))
		self.config['mqtt:port']         = int(os_getenv('MQTT_PORT', default=self.configuration.getint('mqtt', 'port', fallback=1883)))
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
								self.actions[plugin_id] = Action(plugin_id, HAL9000_Plugin_Status(plugin_id), daemon=self)
						case 'trigger':
							Trigger = getattr(module, 'Trigger')
							if Trigger is not None:
								self.triggers[plugin_id] = Trigger(plugin_id, HAL9000_Plugin_Status(plugin_id))
		for section_name in self.configuration.sections():
			plugin_path = self.configuration.getstring(section_name, 'plugin', fallback=None)
			if plugin_path is not None:
				plugin_type, plugin_id = section_name.lower().split(':',1)
				match plugin_type:
					case 'action':
						self.actions[plugin_id].configure(self.configuration, section_name)
					case 'trigger':
						self.triggers[plugin_id].configure(self.configuration, section_name)
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
			if section_name.startswith('script:'):
				script_exec = self.configuration.getstring(section_name, 'exec', fallback=None)
				if script_exec is not None and os_path_exists(script_exec) is True:
					script_name = section_name.split(':', 1).pop()
					self.scripts[script_name] = script_exec


	async def loop(self):
		results = {'main': None}
		try:
			self.scheduler.start()
			startup_timeout = time_monotonic() + self.config['startup:init-timeout']
			plugins = { HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN: {},
			                 HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING: {},
			                 HAL9000_Plugin.PLUGIN_RUNLEVEL_RUNNING: {},
			                 HAL9000_Plugin.PLUGIN_RUNLEVEL_HALTING: {}}
			for plugin in list(self.triggers.values()) + list(self.actions.values()):
				plugin_id = str(plugin)
				plugin_runlevel = plugin.runlevel()
				plugins[plugin_runlevel][plugin_id] = plugin
			self.logger.info(f"Startup initialized (plugins that need runtime registration):")
			for id, plugin in plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN].items():
				self.logger.info(f" - Plugin '{id.split(':').pop()}'")
			self.tasks['signals'] = asyncio_create_task(self.task_signal())
			self.tasks['mqtt'] = asyncio_create_task(self.task_mqtt())
			self.logger.debug(f"STATUS at startup = {self.plugins}")
			while self.plugins['brain'].status == Daemon.BRAIN_STATUS_STARTING:
				for runlevel in [HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN, HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING]:
					if runlevel in plugins:
						for id, plugin in plugins[runlevel].items():
							plugin_runlevel = plugin.runlevel()
							if plugin_runlevel != runlevel:
								self.logger.info(f"Plugin '{id.split(':').pop()}' is now in runlevel '{plugin_runlevel}'")
								plugins[runlevel][id] = None
								plugins[plugin_runlevel][id] = plugin
						plugins[runlevel] = {id:plugin for id,plugin in plugins[runlevel].items() if plugin is not None}
				if startup_timeout is not None:
					if time_monotonic() > startup_timeout:
						self.logger.critical(f"Startup failed (plugins that haven't reported their runlevel):")
						for id, plugin in plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN].items():
							error = plugin.runlevel_error()
							self.logger.critical(f"    Plugin '{id.split(':').pop()}': Error #{error['code']} => {error['message']}")
							self.queue_signal('frontend', {'gui': {'screen': {'name': 'error',
							                                                  'parameter': {'code': error['code'],
							                                                                'message': error['message']}}}})
						self.logger.critical("Terminating due to plugins that haven't reached runlevel 'starting' within timelimit")
						self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
					if len(plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN]) == 0:
						self.logger.info(f"Startup in progress for all plugins")
						startup_timeout = None
						del plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN]
						for plugin in self.plugins.values():
							plugin.addNameCallback(self.on_plugin_callback, '*')
				if startup_timeout is None:
					if HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING in plugins:
						if len(plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING]) == 0:
							del plugins[HAL9000_Plugin.PLUGIN_RUNLEVEL_STARTING]
							self.logger.info(f"Startup completed for all plugins")
							self.plugins['brain'].status = Daemon.BRAIN_STATUS_READY
				await asyncio_sleep(0.1)
			self.logger.debug(f"STATUS after startup = {self.plugins}")
			if self.config['brain:sleep-time'] is not None and self.config['brain:wakeup-time'] is not None:
				try:
					time_sleep = datetime_time.fromisoformat(self.config['brain:sleep-time'])
					time_wakeup = datetime_time.fromisoformat(self.config['brain:wakeup-time'])
					self.scheduler.add_job(self.on_scheduler, apscheduler_triggers_cron_CronTrigger(hour=time_sleep.hour, minute=time_sleep.minute),
					                       args=['brain', {'status': Daemon.BRAIN_STATUS_ASLEEP}], id='brain:sleep', name='brain:sleep')
					self.scheduler.add_job(self.on_scheduler, apscheduler_triggers_cron_CronTrigger(hour=time_wakeup.hour, minute=time_wakeup.minute),
					                       args=['brain', {'status': Daemon.BRAIN_STATUS_AWAKE}], id='brain:wakeup', name='brain:wakeup')
				except Exception as e:
					print(e) # TODO
			while self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
				await asyncio_sleep(0.1)
		except Exception as e:
			self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
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
					case 'hal9000/command/brain/status':
						if self.plugins['brain'].status in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP]:
							if payload in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP, Daemon.BRAIN_STATUS_DYING]:
								self.plugins['brain'].status = payload
					case 'hal9000/command/brain/script':
						if payload in self.scripts:
							self.logger.info(f"Executing configured script with id '{payload}': {self.scripts[payload]}")
							os_system(self.scripts[payload])
					case other:
						if self.plugins['brain'].status in [Daemon.BRAIN_STATUS_STARTING, \
						                                             Daemon.BRAIN_STATUS_READY, \
						                                             Daemon.BRAIN_STATUS_AWAKE]:
							signals = {}
							if topic in self.callbacks['mqtt']:
								triggers = self.callbacks['mqtt'][topic]
								self.logger.debug(f"TRIGGERS: {','.join(str(x).split(':',2).pop(2) for x in triggers)}")
								self.logger.debug(f"STATUS before triggers = {self.plugins}")
								for trigger in triggers:
									signal = trigger.handle(message)
									if signal is not None and bool(signal) is not False:
										trigger_id = str(trigger).split(':', 2)[2]
										signals[trigger_id] = signal
								for trigger_id, signal in signals.items():
									for plugin_name in signal.keys():
										if plugin_name not in self.plugins:
											self.logger.warning(f"SIGNAL for unknown plugin '{plugin_name}' " \
											                    f"generated by trigger '{trigger_id}: '{signal}'")
											continue
										plugin = self.plugins[plugin_name]
										signal = signal[plugin_name]
										self.logger.debug(f"SIGNAL for plugin '{plugin_name}' " \
										                  f"generated by trigger '{trigger_id}': '{signal}'")
										await plugin.signal(signal)
								self.logger.debug(f"STATUS after signals   = {self.plugins}")
		except aiomqtt_MqttError as e:
			if self.tasks['mqtt'].cancelled() is False and self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
				raise e
		except asyncio_CancelledError as e:
			pass


	async def task_mqtt_event_listener(self, mqtt):
		try:
			while self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
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
				self.logger.debug(f"MQTT.subscribe('hal9000/command/brain/status') for plugin 'brain'")
				await mqtt.subscribe('hal9000/command/brain/status')
				self.logger.debug(f"MQTT.subscribe('hal9000/command/brain/script') for plugin 'brain'")
				await mqtt.subscribe('hal9000/command/brain/script')
				for mqtt_topic, trigger in self.callbacks['mqtt'].items():
					self.logger.debug(f"MQTT.subscribe('{mqtt_topic}') for trigger '{str(trigger)}'")
					await mqtt.subscribe(mqtt_topic)
				while self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
					await asyncio_sleep(0.1)
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
			self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
			raise e


	async def task_signal(self):
		try:
			while self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
				if self.signal_queue.empty() is False:
					data = await self.signal_queue.get()
					if isinstance(data, dict) is True and 'plugin' in data and 'signal' in data:
						plugin = data['plugin']
						signal = data['signal']
						self.logger.debug(f"SIGNAL for plugin '{plugin}' generated by Daemon.task_signal(): '{signal}'")
						if plugin in self.plugins:
							plugin = self.plugins[plugin]
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
			self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
			raise e


	async def on_scheduler(self, plugin, signal):
		self.queue_signal(plugin, signal)


	def import_plugin(self, plugin_name: str, class_name: str) -> HAL9000_Plugin:
		plugin = importlib_import_module(plugin_name)
		if plugin is not None:
			return getattr(plugin, class_name)
		return None


	def on_plugin_callback(self, plugin, name, old_value, new_value) -> bool:
		if plugin.plugin_id == 'brain' and name == 'status':
			if new_value not in [Daemon.BRAIN_STATUS_STARTING, Daemon.BRAIN_STATUS_READY, \
			                     Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP, \
			                     Daemon.BRAIN_STATUS_DYING]:
				return False
		logging_getLogger().info(f"Plugin '{plugin.plugin_id}': {name} changes from '{old_value}' to '{new_value}'")
		return True


	def on_brain_status_callback(self, plugin, name, old_status, new_status) -> bool:
		if new_status == Daemon.BRAIN_STATUS_READY:
			next_brain_status = Daemon.BRAIN_STATUS_AWAKE
			if self.config['brain:sleep-time'] is not None and self.config['brain:wakeup-time'] is not None:
				time_now = datetime_datetime.now().time()
				time_sleep = datetime_time.fromisoformat(self.config['brain:sleep-time'])
				time_wakeup = datetime_time.fromisoformat(self.config['brain:wakeup-time'])
				if time_sleep > time_wakeup:
					if time_now > time_sleep or time_now < time_wakeup:
						next_brain_status = Daemon.BRAIN_STATUS_ASLEEP
				else:
					if time_now > time_sleep and time_now < time_wakeup:
						next_brain_status = Daemon.BRAIN_STATUS_ASLEEP
			self.queue_signal('brain', {'status': next_brain_status})
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin_Status, signal: dict) -> None:
		if 'status' in signal:
			match self.plugins['brain'].status:
				case Daemon.BRAIN_STATUS_STARTING:
					if signal['status'] == Daemon.BRAIN_STATUS_READY:
						self.plugins['brain'].status = signal['status']
				case Daemon.BRAIN_STATUS_READY:
					if signal['status'] in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP]:
						self.plugins['brain'].status = signal['status']
				case Daemon.BRAIN_STATUS_AWAKE:
					if signal['status'] in [Daemon.BRAIN_STATUS_ASLEEP, Daemon.BRAIN_STATUS_DYING]:
						self.plugins['brain'].status = signal['status']
				case Daemon.BRAIN_STATUS_ASLEEP:
					if signal['status'] in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_DYING]:
						self.plugins['brain'].status = signal['status']
				case Daemon.BRAIN_STATUS_DYING:
					pass


	async def signal(self, plugin: str, signal: dict) -> None:
		if plugin in self.plugins:
			await self.plugins[plugin].signal(signal)


	def queue_signal(self, plugin: str, signal: dict) -> None:
		self.signal_queue.put_nowait({'plugin': plugin, 'signal': signal})


	def schedule_signal(self, seconds: int, receiver: str, signal: dict, id=None) -> None:
		self.scheduler.add_job(self.on_scheduler, apscheduler_triggers_date_DateTrigger(datetime_datetime.now() + datetime_timedelta(seconds=seconds)),
		                       args=[receiver, signal], id=id, name=id, replace_existing=True)


	def cancel_signal(self, id: str) -> None:
		if self.scheduler.get_job(id) is not None:
			self.scheduler.remove_job(id)


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
		self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING

