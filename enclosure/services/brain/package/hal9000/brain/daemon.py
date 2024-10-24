from typing import Any
from enum import StrEnum as enum_StrEnum
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
                    getLevelName as logging_getLevelName, \
                    addLevelName as logging_addLevelName
from logging.config import fileConfig as logging_config_fileConfig
from configparser import ConfigParser as configparser_ConfigParser
from importlib import import_module as importlib_import_module
from inspect import stack as inspect_stack
from signal import signal as signal_signal, \
                   SIGHUP as signal_SIGHUP, \
                   SIGTERM as signal_SIGTERM, \
                   SIGQUIT as signal_SIGQUIT, \
                   SIGINT as signal_SIGINT, \
                   strsignal as signal_strsignal
from asyncio import create_task as asyncio_create_task, \
                    gather as asyncio_gather, \
                    sleep as asyncio_sleep, \
                    Queue as asyncio_Queue, \
                    CancelledError as asyncio_CancelledError

from aiomqtt import Client as aiomqtt_Client, \
                    Will as aiomqtt_Will, \
                    MqttError as aiomqtt_MqttError
from apscheduler.schedulers.asyncio import AsyncIOScheduler as apscheduler_schedulers_AsyncIOScheduler
from dbus_fast.aio import MessageBus
from dbus_fast.auth import AuthExternal, UID_NOT_SPECIFIED
from dbus_fast.constants import BusType

from .plugin import HAL9000_Plugin, DataInvalid, RUNLEVEL, CommitPhase
from .plugins.brain import STATUS


class Daemon(object):
	LOGLEVEL_TRACE = 5

	def __init__(self) -> None:
		self.logger = logging_getLogger()
		self.config = {}
		self.plugins = {}
		self.callbacks = {'mqtt': {}}
		self.tasks = {}
		self.signal_queue = asyncio_Queue()
		self.mqtt_publish_queue = asyncio_Queue()
		self.scheduler = apscheduler_schedulers_AsyncIOScheduler()
		self.runlevel_inhibitors = {RUNLEVEL.STARTING: {}, RUNLEVEL.READY: {}, RUNLEVEL.RUNNING: {}}


	def configure(self, filename: str) -> None:
		logging_addLevelName(Daemon.LOGLEVEL_TRACE, 'TRACE')
		logging_config_fileConfig(filename)
		logging_getLogger('apscheduler').setLevel('ERROR')
		self.logger.info(f"[daemon] LOADING CONFIGURATION '{filename}'")
		self.logger.info(f"[daemon] Log-level set to '{logging_getLevelName(self.logger.level)}'")
		self.configuration = configparser_ConfigParser(delimiters='=', \
		                                               converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')], \
		                                                           'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
		self.configuration.read(filename)
		self.logger.debug(f"[daemon] loading plugins....")
		actions = {}
		triggers = {}
		for section_name in self.configuration.sections():
			plugin_path = self.configuration.getstring(section_name, 'plugin', fallback=None)
			plugin_hidden = self.configuration.getboolean(section_name, 'hidden', fallback=False)
			if plugin_path is not None:
				module = importlib_import_module(plugin_path)
				if module is not None:
					plugin_type, plugin_name = section_name.lower().split(':',1)
					match plugin_type.lower():
						case 'action':
							Action = getattr(module, 'Action')
							if Action is not None:
								actions[plugin_name] = Action(plugin_name, daemon=self, hidden=plugin_hidden)
						case 'trigger':
							Trigger = getattr(module, 'Trigger')
							if Trigger is not None:
								triggers[plugin_name] = Trigger(plugin_name, daemon=self, hidden=plugin_hidden)
		self.logger.debug(f"[daemon] configuring plugins....")
		for section_name in self.configuration.sections():
			plugin_path = self.configuration.getstring(section_name, 'plugin', fallback=None)
			if plugin_path is not None:
				plugin_type, plugin_name = section_name.lower().split(':',1)
				match plugin_type:
					case 'action':
						actions[plugin_name].configure(self.configuration, section_name)
					case 'trigger':
						triggers[plugin_name].configure(self.configuration, section_name)
		self.logger.debug(f"[daemon] registering callbacks for trigger plugins....")
		for trigger_id in triggers.keys():
			trigger = triggers[trigger_id]
			callbacks = trigger.callbacks()
			for callback_type in callbacks.keys():
				if callback_type.lower() == 'mqtt':
					callback_list = callbacks[callback_type]
					for mqtt_topic in callback_list:
						if mqtt_topic not in self.callbacks['mqtt']:
							self.callbacks['mqtt'][mqtt_topic] = []
						self.callbacks['mqtt'][mqtt_topic].append(trigger)
		self.logger.debug(f"[daemon] reading daemon specific settings....")
		self.config['mqtt:server'] = str(os_getenv('MQTT_SERVER', default=self.configuration.getstring('mqtt', 'server', fallback='127.0.0.1')))
		self.config['mqtt:port']   = int(os_getenv('MQTT_PORT', default=self.configuration.getint('mqtt', 'port', fallback=1883)))
		self.config['help:error-url']  = self.configuration.getstring('help', 'error-url',  fallback='https://github.com/juergenpabel/HAL9000/wiki/Error-database')
		self.config['help:splash-url'] = self.configuration.getstring('help', 'splash-url', fallback='https://github.com/juergenpabel/HAL9000/wiki/Splashs')
		self.add_runlevel_inhibitor(RUNLEVEL.STARTING, 'plugins:runlevel', self.runlevel_inhibitor_starting_plugins)
		self.logger.debug(f"[daemon] Daemon configuration completed")


	async def loop(self) -> dict:
		self.logger.info(f"[daemon] Application logic is about to run")
		signal_signal(signal_SIGHUP, self.on_posix_signal)
		signal_signal(signal_SIGTERM, self.on_posix_signal)
		signal_signal(signal_SIGQUIT, self.on_posix_signal)
		signal_signal(signal_SIGINT, self.on_posix_signal)
		results = await self.runlevel_starting()
		if len(results) == 0 and self.plugins['brain'].status != STATUS.DYING:
			results = await self.runlevel_ready()
		if len(results) == 0 and self.plugins['brain'].status != STATUS.DYING:
			results = await self.runlevel_running()
		self.logger.info(f"[daemon] Application logic has ended")
		self.logger.debug(f"[daemon] gathering tasks and exiting...")
		for name, task in self.tasks.copy().items():
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.loop() cancelling and gathering task '{name}'...")
			task.cancel()
			results[name] = (await asyncio_gather(task, return_exceptions=True)).pop()
		self.scheduler.shutdown()
		return results


	async def runlevel_starting(self) -> dict:
		self.logger.info(f"[daemon] Brain: {RUNLEVEL.STARTING}")
		self.logger.debug(f"[daemon] STATUS at runlevel '{self.plugins['brain'].runlevel}' = {self}")
		try:
			self.scheduler.start()
			self.tasks['signals'] = asyncio_create_task(self.task_signal())
			self.tasks['mqtt'] = asyncio_create_task(self.task_mqtt())
			while 'mqtt:publisher' not in self.tasks and 'mqtt:subscriber' not in self.tasks:
				if self.plugins['brain'].status == STATUS.DYING:
					self.logger.debug(f"[daemon] status changed to 'dying', raising exception while waiting for MQTT connection in runlevel 'starting'")
					raise RuntimeError(STATUS.DYING)
				await asyncio_sleep(0.1)
			self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/runlevel', 'payload': 'starting'})
			self.logger.info(f"[daemon] Connected to MQTT, now requesting runlevel announcements from these services:")
			for name, plugin in dict(filter(lambda item: item[1].runlevel == DataInvalid.UNKNOWN, self.plugins.items())).items():
				self.logger.info(f"[daemon] - Service '{name}'")
				self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/command/{name}/runlevel', 'payload': None})
			self.logger.info(f"[daemon] Waiting for these services to announce their runlevel...")
			while len(list(filter(lambda plugin: plugin.runlevel == DataInvalid.UNKNOWN, self.plugins.values()))) > 0:
				if self.plugins['brain'].status == STATUS.DYING:
					self.logger.debug(f"[daemon] status changed to 'dying', raising exception while waiting for plugins in runlevel 'starting'")
					raise RuntimeError(STATUS.DYING)
				await asyncio_sleep(0.1)
			self.logger.info(f"[daemon] ...all services announced their runlevel")
			self.logger.debug(f"[daemon] Inhibitors in runlevel '{RUNLEVEL.STARTING}': " \
			                  f"{', '.join(list(self.runlevel_inhibitors[RUNLEVEL.STARTING].keys()))}...")
			self.logger.info(f"[daemon] Waiting for inhibitors in runlevel '{RUNLEVEL.STARTING}'to finish...")
			while len(self.runlevel_inhibitors[RUNLEVEL.STARTING]) > 0:
				self.evaluate_runlevel_inhibitors(RUNLEVEL.STARTING)
				if self.plugins['brain'].status == STATUS.DYING:
					self.logger.debug(f"[daemon] status changed to 'dying', raising exception while waiting for inhibitors in runlevel 'starting'")
					raise RuntimeError(STATUS.DYING)
				await asyncio_sleep(0.1)
			self.logger.info(f"[daemon] ...all inhibitors in runlevel '{RUNLEVEL.STARTING}' have finished")
			self.logger.debug(f"[daemon] STATUS after runlevel 'starting' = {self}")
		except Exception as e:
			self.logger.debug(f"[daemon] execution of runlevel '{RUNLEVEL.STARTING}' aborted, services that haven't announced their runlevel: " \
			                  f"{', '.join(list(dict(filter(lambda item: item[1].runlevel == DataInvalid.UNKNOWN, self.plugins.items())).keys()))}")
			self.logger.info(f"[daemon] Execution of runlevel '{RUNLEVEL.STARTING}' aborted, remaining inhibitors that haven't finished:")
			for name in list(self.runlevel_inhibitors[RUNLEVEL.STARTING].keys()):
				self.logger.info(f"[daemon] - Inhibitor '{name}'")
			self.logger.critical(f"[daemon] Daemon.runlevel_starting(): {type(e).__name__} => {str(e)}")
			from traceback import format_exc as traceback_format_exc
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] {traceback_format_exc()}")
			if str(e) != STATUS.DYING:
				self.plugins['brain'].status = STATUS.DYING, CommitPhase.COMMIT
				return {'main': e}
		self.plugins['brain'].runlevel = RUNLEVEL.READY, CommitPhase.COMMIT
		return {}

			
	async def runlevel_ready(self) -> dict:
		self.logger.info(f"[daemon] Brain: {RUNLEVEL.READY}")
		self.logger.debug(f"[daemon] STATUS in runlevel '{self.plugins['brain'].runlevel}' = {self}")
		try:
			self.plugins['brain'].status = STATUS.AWAKE
			self.queue_signal('brain', {'time:sync': {}})
			self.logger.debug(f"[daemon] Inhibitors in runlevel '{RUNLEVEL.READY}': " \
			                  f"{', '.join(list(self.runlevel_inhibitors[RUNLEVEL.READY].keys()))}...")
			self.logger.info(f"[daemon] Waiting for inhibitors in runlevel '{RUNLEVEL.READY}'to finish...")
			while len(self.runlevel_inhibitors[RUNLEVEL.READY]) > 0:
				if self.plugins['brain'].status == STATUS.DYING:
					self.logger.debug(f"[daemon] status changed to 'dying', raising exception while waiting for inhibitos in runlevel 'ready'")
					raise RuntimeError(STATUS.DYING)
				self.evaluate_runlevel_inhibitors(RUNLEVEL.READY)
				await asyncio_sleep(0.1)
			self.logger.info(f"[daemon] ...all inhibitors in runlevel '{RUNLEVEL.READY}' have finished")
			self.logger.debug(f"[daemon] STATUS after runlevel 'ready' = {self}")
		except Exception as e:
			self.logger.info(f"[daemon] Execution of runlevel '{RUNLEVEL.READY}' aborted, remaining inhibitors that haven't finished: ")
			for name in list(self.runlevel_inhibitors[RUNLEVEL.READY].keys()):
				self.logger.info(f"[daemon] - Inhibitor '{name}'")
			self.logger.critical(f"[daemon] Daemon.runlevel_ready(): {type(e).__name__} => {str(e)}")
			from traceback import format_exc as traceback_format_exc
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] {traceback_format_exc()}")
			if str(e) == STATUS.DYING:
				e = None
			self.plugins['brain'].status = STATUS.DYING, CommitPhase.COMMIT
			return {'main': e}
		self.plugins['brain'].runlevel = RUNLEVEL.RUNNING, CommitPhase.COMMIT
		return {}


	async def runlevel_running(self) -> dict:
		self.logger.info(f"[daemon] Brain: {RUNLEVEL.RUNNING}")
		self.logger.debug(f"[daemon] STATUS in runlevel '{self.plugins['brain'].runlevel}' = {self}")
		try:
			while self.plugins['brain'].runlevel == RUNLEVEL.RUNNING and self.plugins['brain'].status != STATUS.DYING:
				await asyncio_sleep(0.1)
			self.logger.debug(f"[daemon] STATUS after runlevel '{self.plugins['brain'].runlevel}' = {self}")
		except Exception as e:
			self.logger.critical(f"[daemon] Daemon.runlevel_running(): {type(e).__name__} => {str(e)}")
			from traceback import format_exc as traceback_format_exc
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] {traceback_format_exc()}")
			if str(e) != STATUS.DYING:
				self.plugins['brain'].status = STATUS.DYING, CommitPhase.COMMIT
				return {'main': e}
		self.plugins['brain'].runlevel = RUNLEVEL.KILLED, CommitPhase.COMMIT
		return {}


	def add_runlevel_inhibitor(self, runlevel: str, name: str, callback) -> None:
		if runlevel in self.runlevel_inhibitors:
			if name not in self.runlevel_inhibitors[runlevel]:
				self.runlevel_inhibitors[runlevel][name] = callback


	def remove_runlevel_inhibitor(self, runlevel: str, name: str) -> None:
		if runlevel in self.runlevel_inhibitors:
			if name in self.runlevel_inhibitors[runlevel]:
				del self.runlevel_inhibitors[runlevel][name]


	def evaluate_runlevel_inhibitors(self, runlevel: str) -> None:
		for name, callback in self.runlevel_inhibitors[runlevel].copy().items():
			if callback() is True:
				self.logger.debug(f"[daemon] Inhibitor '{name}' has finished")
				del self.runlevel_inhibitors[runlevel][name]


	def runlevel_inhibitor_starting_plugins(self) -> bool:
		for name, plugin in self.plugins.items():
			if name != 'brain' and plugin.runlevel != RUNLEVEL.RUNNING:
				return False
		return True


	async def task_mqtt_subscriber(self, mqtt: aiomqtt_Client) -> None:
		self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_subscriber() running")
		try:
			async for message in mqtt.messages:
				topic = message.topic.value
				payload = message.payload.decode('utf-8', 'surrogateescape')
				self.logger.debug(f"[daemon] MQTT received: {topic} => {str(chr(0x27))+str(chr(0x27)) if payload == '' else payload}")
				match topic:
					case 'hal9000/command/brain/status':
						if self.plugins['brain'].status in [STATUS.AWAKE, STATUS.ASLEEP]:
							if payload in [STATUS.AWAKE, STATUS.ASLEEP, STATUS.DYING]:
								self.plugins['brain'].status = payload
					case other:
						signals = {}
						if topic in self.callbacks['mqtt']:
							triggers = self.callbacks['mqtt'][topic]
							if self.plugins['brain'].status == STATUS.ASLEEP:
								triggers = [trigger for trigger in triggers if trigger.module.sleepless is True]
							self.logger.debug(f"[daemon] TRIGGERS: {','.join(str(x) for x in triggers)}")
							self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_subscriber() STATUS before triggers = " \
							                                       f"{self.plugins}")
							for trigger in triggers:
								signal = trigger.handle(message)
								if signal is not None and len(signal) > 0:
									signals[str(trigger)] = signal
						self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_subscriber() SIGNALS generated by TRIGGERS: {signals}")
						for trigger_id, signal in signals.items():
							plugin_name = signal[0]
							signal = signal[1]
							if plugin_name not in self.plugins:
								self.logger.warning(f"[daemon] SIGNAL for unknown plugin '{plugin_name}' " \
								                    f"generated by trigger '{trigger_id}: '{signal}'")
							else:
								self.logger.debug(f"[daemon] SIGNAL for plugin '{plugin_name}' " \
								                  f"generated by trigger '{trigger_id}': '{signal}'")
								await self.plugins[plugin_name].signal(signal)
						self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_subscriber() STATUS after signals   = {self.plugins}")
		except asyncio_CancelledError as e:
			pass
		except Exception as e:
			if self.tasks['mqtt'].cancelled() is False and self.plugins['brain'].status != STATUS.DYING:
				self.logger.critical(f"[daemon] task 'mqtt_subscriber' exiting due to : {type(e).__name__} => {str(e)}")
				raise e
		finally:
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_subscriber() exiting")
			self.plugins['brain'].status = STATUS.DYING


	async def task_mqtt_publisher(self, mqtt: aiomqtt_Client) -> None:
		self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_publisher() running")
		try:
			while self.plugins['brain'].status != STATUS.DYING:
				if self.mqtt_publish_queue.empty() is False:
					data = await self.mqtt_publish_queue.get()
					if isinstance(data, dict) is True and 'topic' in data and 'payload' in data:
						topic = data['topic']
						payload = data['payload']
						if isinstance(payload, dict) is True:
							payload = json_dumps(payload)
						await mqtt.publish(topic, payload)
						self.logger.debug(f"[daemon] MQTT published: {topic} => {str(chr(0x27))+str(chr(0x27)) if payload == '' else payload}")
				await asyncio_sleep(0.01)
		except asyncio_CancelledError as e:
			pass
		finally:
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_publisher() exiting")
			self.plugins['brain'].status = STATUS.DYING


	async def task_mqtt(self) -> None:
		self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() running")
		try:
			self.logger.info(f"[daemon] MQTT.connect(host='{self.config['mqtt:server']}', port={self.config['mqtt:port']}) for plugin 'brain'")
			async with aiomqtt_Client(self.config['mqtt:server'], self.config['mqtt:port'], \
			                          will=aiomqtt_Will('hal9000/event/brain/runlevel', RUNLEVEL.KILLED), \
			                          identifier='hal9000-brain') as mqtt:
				self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() MQTT.subscribe('hal9000/command/brain/status') for plugin 'brain'")
				await mqtt.subscribe('hal9000/command/brain/status')
				for mqtt_topic, trigger in self.callbacks['mqtt'].items():
					await mqtt.subscribe(mqtt_topic)
					self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() MQTT.subscribe('{mqtt_topic}') for trigger '{str(trigger)}'")
				self.tasks['mqtt:publisher'] = asyncio_create_task(self.task_mqtt_publisher(mqtt))
				self.tasks['mqtt:subscriber'] = asyncio_create_task(self.task_mqtt_subscriber(mqtt))
				try:
					while self.plugins['brain'].status != STATUS.DYING:
						await asyncio_sleep(0.1)
				finally:
					await mqtt.publish('hal9000/event/brain/runlevel', 'killed') # aiomqtt's will=... somehow doesn't work
		except asyncio_CancelledError as e:
			self.logger.debug(f"[daemon] task mqtt has been cancelled")
		except Exception as e:
			self.logger.critical(f"[daemon] {str(e)}")
			raise e
		finally:
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() exiting")
			self.plugins['brain'].status = STATUS.DYING


	async def task_signal(self) -> None:
		self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_signal() running")
		try:
			while self.plugins['brain'].status != STATUS.DYING:
				if self.signal_queue.empty() is False:
					data = await self.signal_queue.get()
					if isinstance(data, dict) is True and 'plugin' in data and 'signal' in data:
						plugin = data['plugin']
						signal = data['signal']
						self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_signal() SIGNAL for plugin '{plugin}': '{signal}'")
						if plugin == '*':
							for plugin in self.plugins.values():
								await plugin.signal(signal)
						elif plugin in self.plugins:
							await self.plugins[plugin].signal(signal)
						else:
							self.logger.warning(f"[daemon] Ignoring SIGNAL for unknown plugin '{plugin}' - ignoring it (=> BUG)")
					else:
						self.logger.warning(f"[daemon] Ignoring invalid SIGNAL '{str(signal)}' from signal_queue")
				await asyncio_sleep(0.01)
		except asyncio_CancelledError as e:
			self.signal_queue = None
		except Exception as e:
			self.plugins['brain'].status = STATUS.DYING
			self.logger.critical(f"[daemon] Daemon.task_signal(): {type(e).__name__} => {str(e)}")
			from traceback import format_exc as traceback_format_exc
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] {traceback_format_exc()}")
			raise e
		finally:
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_signal() exiting")
			self.plugins['brain'].status = STATUS.DYING


	async def on_scheduler(self, plugin: str, signal: dict) -> None:
		self.queue_signal(plugin, signal)


	def import_plugin(self, plugin_name: str, class_name: str) -> HAL9000_Plugin:
		plugin = importlib_import_module(plugin_name)
		if plugin is not None:
			return getattr(plugin, class_name)
		return None


	def process_error(self, level: str, id: str, title: str, details: str = '<no details>') -> None:
		self.logger.log(getattr(logging, level.upper()), f"[daemon] ERROR #{id}: {title} => {details}")
		if self.plugins['brain'].runlevel == RUNLEVEL.RUNNING and self.plugins['brain'].status == STATUS.AWAKE:
			url = self.substitute_vars(self.config['help:error-url'], {'error_id': id})
			self.queue_signal('*', {'error': {'id': id, 'url': url, 'title': title, 'details': details}})


	def queue_signal(self, plugin: str, signal: dict) -> None:
		if self.logger.isEnabledFor(Daemon.LOGLEVEL_TRACE) is True:
			self.add_caller_trace(signal)
		self.signal_queue.put_nowait({'plugin': plugin, 'signal': signal})


	def create_scheduled_signal(self, seconds: float, plugin: str, signal: dict, id: str | None = None, mode: str = 'single') -> None:
		if self.logger.isEnabledFor(Daemon.LOGLEVEL_TRACE) is True:
			self.add_caller_trace(signal, f"scheduled as '{mode}' with id='{id}'")
		match mode:
			case 'single':
				run_date = datetime_datetime.now() + datetime_timedelta(seconds=int(seconds), microseconds=int((seconds - int(seconds)) * 1000000))
				self.scheduler.add_job(self.on_scheduler, 'date', run_date=run_date, args=[plugin, signal], id=id, name=id, replace_existing=True)
			case 'interval':
				self.scheduler.add_job(self.on_scheduler, 'interval', seconds=int(seconds), args=[plugin, signal], id=id, name=id, replace_existing=True)
			case 'cron':
				hour=int(seconds/3600)
				minute=int((seconds%3600)/60)
				self.scheduler.add_job(self.on_scheduler, 'cron', hour=hour, minute=minute, args=[plugin, signal], id=id, name=id, replace_existing=True)
			case other:
				logging_getLogger().error(f"unsupported schedule mode '{mode}' in Daemon.create_scheduled_signal()")


	def remove_scheduled_signal(self, id: str) -> None:
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


	def on_posix_signal(self, number: int, frame) -> None:
		logging_getLogger().info(f"[Daemon] Received signal {number} ({signal_strsignal(number).upper()}), preparing to exit")
		self.plugins['brain'].status = STATUS.DYING


	def __repr__(self) -> str:
		result = []
		for name in sorted(self.plugins.keys()):
			plugin = self.plugins[name]
			if plugin.module.hidden is False:
				result.append(f"'{name}': {plugin}")
		return ', '.join(result)


	def substitute_vars(self, data: Any, vars: dict) -> Any:
		try:
			if isinstance(data, list) is True:
				for index, value in enumerate(data):
					data[index] = self.substitute_vars(value, vars)
			if isinstance(data, dict) is True:
				for key, value in data.items():
					data[key] = self.substitute_vars(value, vars)
			if isinstance(data, str) is True:
				data = data.format(**vars)
		except KeyError as e:
			if str(e).isidentifier() is True:
				logging_getLogger().warn(f"encountered unknown variable '{str(e)}' during substition")
				logging_getLogger().debug(f"substition data (type={type(data)}): {str(data)}")
				logging_getLogger().debug(f"substition vars (type={type(vars)}): {str(vars)}")
		return data


	def add_caller_trace(self, signal: dict, trace_notice: str = '', stack_offset: int = 2) -> None:
		if isinstance(signal, dict) is True:
			stack = inspect_stack()
			if stack_offset < len(stack):
				fi = stack.pop(stack_offset)
				caller = fi.function
				if 'self' in fi.frame.f_locals:
					caller = f"{fi.frame.f_locals['self'].id}<{fi.function}>"
				signal['trace'] = caller
				if trace_notice != '':
					signal['trace'] += f' ({trace_notice})'
			del stack # cycle breaking for GC

