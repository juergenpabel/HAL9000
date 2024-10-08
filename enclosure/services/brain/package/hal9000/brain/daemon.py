from typing import Any
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
import logging
from logging import getLogger as logging_getLogger, \
                    getLevelName as logging_getLevelName, \
                    addLevelName as logging_addLevelName
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
                    Will as aiomqtt_Will, \
                    MqttError as aiomqtt_MqttError
from apscheduler.schedulers.asyncio import AsyncIOScheduler as apscheduler_schedulers_AsyncIOScheduler
from dbus_fast.aio import MessageBus
from dbus_fast.auth import AuthExternal, UID_NOT_SPECIFIED
from dbus_fast.constants import BusType


from .plugin import HAL9000_Plugin, HAL9000_Plugin_Data, CommitPhase


class Daemon(object):

	BRAIN_STATUS_LAUNCHING = 'launching'
	BRAIN_STATUS_AWAKE = 'awake'
	BRAIN_STATUS_ASLEEP = 'asleep'
	BRAIN_STATUS_DYING = 'dying'

	BRAIN_TIME_UNSYNCHRONIZED = 'unsynchronized'
	BRAIN_TIME_SYNCHRONIZED =   'synchronized'

	LOGLEVEL_TRACE = 5

	def __init__(self) -> None:
		self.logger = logging_getLogger()
		self.config = {}
		self.plugins = {}
		self.plugins['brain'] = HAL9000_Plugin_Data('brain', runlevel=HAL9000_Plugin.RUNLEVEL_STARTING, status=Daemon.BRAIN_STATUS_LAUNCHING)
		self.plugins['brain'].addLocalNames(['time'])
		self.tasks = {}
		self.actions = {}
		self.triggers = {}
		self.callbacks = {'mqtt': {}}
		self.signal_queue = asyncio_Queue()
		self.mqtt_publish_queue = asyncio_Queue()
		self.scheduler = apscheduler_schedulers_AsyncIOScheduler()
		signal_signal(signal_SIGHUP, self.on_posix_signal)
		signal_signal(signal_SIGTERM, self.on_posix_signal)
		signal_signal(signal_SIGQUIT, self.on_posix_signal)
		signal_signal(signal_SIGINT, self.on_posix_signal)


	def configure(self, filename: str) -> None:
		logging_addLevelName(Daemon.LOGLEVEL_TRACE, 'TRACE')
		logging_config_fileConfig(filename)
		logging_getLogger('apscheduler').setLevel('ERROR')
		self.logger.info(f"[daemon] LOADING CONFIGURATION '{filename}'")
		self.logger.info(f"[daemon] Log-level set to '{logging_getLevelName(self.logger.level)}'")
		self.configuration = configparser_ConfigParser(delimiters='=',
		                                               converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
		                                                           'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
		self.configuration.read(filename)
		self.config['mqtt:server']       = str(os_getenv('MQTT_SERVER', default=self.configuration.getstring('mqtt', 'server', fallback='127.0.0.1')))
		self.config['mqtt:port']         = int(os_getenv('MQTT_PORT', default=self.configuration.getint('mqtt', 'port', fallback=1883)))
		self.config['startup:init-timeout'] = self.configuration.getint('startup', 'init-timeout', fallback=30)
		self.config['brain:sleep-time']  = self.configuration.get('brain', 'sleep-time', fallback=None)
		self.config['brain:wakeup-time'] = self.configuration.get('brain', 'wakeup-time', fallback=None)
		self.config['help:error-url'] = self.configuration.getstring('help', 'error-url', fallback='https://github.com/juergenpabel/HAL9000/wiki/Error-database')
		self.config['help:splash-url'] = self.configuration.getstring('help', 'splash-url', fallback='https://github.com/juergenpabel/HAL9000/wiki/Splashs')
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
								self.actions[plugin_id] = Action(plugin_id, HAL9000_Plugin_Data(plugin_id), daemon=self)
						case 'trigger':
							Trigger = getattr(module, 'Trigger')
							if Trigger is not None:
								self.triggers[plugin_id] = Trigger(plugin_id, HAL9000_Plugin_Data(plugin_id))
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
							self.callbacks['mqtt'][mqtt_topic] = []
						self.callbacks['mqtt'][mqtt_topic].append(trigger)


	async def loop(self) -> dict:
		results = await self.starting()
		if bool(results) is False:
			results = await self.running()
		self.logger.debug(f"[daemon] gathering tasks and exiting...")
		for name, task in self.tasks.copy().items():
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.loop() cancelling and gathering task '{name}'...")
			task.cancel()
			results[name] = (await asyncio_gather(task, return_exceptions=True)).pop()
		return results


	async def starting(self) -> dict:
		self.logger.debug(f"[daemon] Daemon starting...")
		self.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.plugins['brain'].addNameCallback(self.on_plugin_callback, '*')
		self.plugins['brain'].addSignalHandler(self.on_brain_signal)
		try:
			self.scheduler.start()
			self.tasks['signals'] = asyncio_create_task(self.task_signal())
			self.tasks['mqtt'] = asyncio_create_task(self.task_mqtt())
			while 'mqtt:publisher' not in self.tasks and 'mqtt:subscriber' not in self.tasks:
				await asyncio_sleep(0.1)
			self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/runlevel', 'payload': 'starting'})
			startup_plugins = list(self.triggers.values()) + list(self.actions.values())
			startup_plugins = list(filter(lambda plugin: plugin.runlevel() == HAL9000_Plugin.RUNLEVEL_UNKNOWN, startup_plugins))
			self.logger.info(f"[daemon] Startup initialized (plugins that need runtime registration):")
			for plugin in filter(lambda plugin: plugin.runlevel() == HAL9000_Plugin.RUNLEVEL_UNKNOWN, startup_plugins):
				plugin_name = str(plugin).split(':').pop()
				self.logger.info(f"[daemon]  - Plugin '{plugin_name}'")
				self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/command/{plugin_name}/runlevel', 'payload': None})
			self.logger.debug(f"[daemon] STATUS at startup = {self.plugins}")
			startup_init_timeout = time_monotonic() + self.config['startup:init-timeout']
			while self.plugins['brain'].runlevel == HAL9000_Plugin.RUNLEVEL_STARTING and self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
				if startup_init_timeout is not None:
					if time_monotonic() > startup_init_timeout:
						self.logger.critical(f"[daemon] Startup failed (plugins that haven't reported their runlevel):")
						for plugin in startup_plugins:
							if plugin.runlevel() == HAL9000_Plugin.RUNLEVEL_UNKNOWN:
								id = str(plugin)
								error = plugin.runlevel_error()
								self.process_error('critical', error['id'], f"    Plugin '{id.split(':').pop()}'", error['title'])
						self.logger.debug(f"[daemon] STATUS at startup-timeout = {self.plugins}")
						self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
					if len(list(filter(lambda plugin: plugin.runlevel() == HAL9000_Plugin.RUNLEVEL_UNKNOWN, startup_plugins))) == 0:
						self.logger.info(f"[daemon] Startup in progress for all plugins")
						for plugin in startup_plugins:
							plugin_name = str(plugin).split(':').pop()
							self.plugins[plugin_name].addNameCallback(self.on_plugin_callback, '*')
						startup_init_timeout = None
				if startup_init_timeout is None:
					if len(list(filter(lambda plugin: plugin.runlevel() == HAL9000_Plugin.RUNLEVEL_RUNNING, startup_plugins))) == len(startup_plugins):
						self.logger.info(f"[daemon] Startup completed for all plugins")
						self.plugins['brain'].runlevel = HAL9000_Plugin.RUNLEVEL_READY
						self.queue_signal('brain', {'time:sync': {}})
				await asyncio_sleep(0.1)
			if self.plugins['brain'].status == Daemon.BRAIN_STATUS_DYING:
				return {}
			self.logger.debug(f"[daemon] STATUS after startup = {self.plugins}")
			if self.config['brain:sleep-time'] is not None:
				try:
					time_sleep = datetime_time.fromisoformat(self.config['brain:sleep-time'])
					self.scheduler.add_job(self.on_scheduler, 'cron', hour=time_sleep.hour, minute=time_sleep.minute,
					                       args=['brain', {'status': Daemon.BRAIN_STATUS_ASLEEP}], id='brain:sleep', name='brain:sleep')
				except ValueError as e:
					self.logger.error(f"[daemon] sleep-time: failed to parse '{self.config['brain:sleep-time']}' as (an ISO-8601 formatted) time")
			if self.config['brain:wakeup-time'] is not None:
				try:
					time_wakeup = datetime_time.fromisoformat(self.config['brain:wakeup-time'])
					self.scheduler.add_job(self.on_scheduler, 'cron', hour=time_wakeup.hour, minute=time_wakeup.minute,
					                       args=['brain', {'status': Daemon.BRAIN_STATUS_AWAKE}], id='brain:wakeup', name='brain:wakeup')
				except ValueError as e:
					self.logger.error(f"[daemon] wakeup-time: failed to parse '{self.config['brain:wakeup-time']}' as (an ISO-8601 formatted) time")
		except Exception as e:
			self.logger.debug(f"[daemon] {e}")
			self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
			return {'main': e}
		return {}

			
	async def running(self) -> dict:
		self.logger.debug(f"[daemon] Daemon running...")
		try:
			while self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
				await asyncio_sleep(0.1)
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.loop() ...dying")
		except Exception as e:
			self.logger.debug(f"[daemon] {e}")
			self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
			return {'main': e}
		return {}


	async def task_mqtt_subscriber(self, mqtt: aiomqtt_Client) -> None:
		self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_subscriber() running")
		try:
			async for message in mqtt.messages:
				topic = message.topic.value
				payload = message.payload.decode('utf-8', 'surrogateescape')
				self.logger.debug(f"[daemon] MQTT received: {topic} => {str(chr(0x27))+str(chr(0x27)) if payload == '' else payload}")
				match topic:
					case 'hal9000/command/brain/status':
						if self.plugins['brain'].status in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP]:
							if payload in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP, Daemon.BRAIN_STATUS_DYING]:
								self.plugins['brain'].status = payload
					case other:
						signals = {}
						if topic in self.callbacks['mqtt']:
							triggers = self.callbacks['mqtt'][topic]
							if self.plugins['brain'].status == Daemon.BRAIN_STATUS_ASLEEP:
								triggers = [trigger for trigger in triggers if trigger.sleepless is True]
							self.logger.debug(f"[daemon] TRIGGERS: {','.join(str(x).split(':',2).pop(2) for x in triggers)}")
							self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_subscriber() STATUS before triggers = {self.plugins}")
							for trigger in triggers:
								signal = trigger.handle(message)
								if signal is not None and bool(signal) is not False:
									signals[str(trigger).split(':', 2).pop(2)] = signal
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
		except aiomqtt_MqttError as e:
			if self.tasks['mqtt'].cancelled() is False and self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
				raise e
		except asyncio_CancelledError as e:
			pass
		finally:
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_subscriber() exiting")


	async def task_mqtt_publisher(self, mqtt: aiomqtt_Client) -> None:
		self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_publisher() running")
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
						self.logger.debug(f"[daemon] MQTT published: {topic} => {str(chr(0x27))+str(chr(0x27)) if payload == '' else payload}")
				await asyncio_sleep(0.01)
		except asyncio_CancelledError as e:
			pass
		finally:
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt_publisher() exiting")


	async def task_mqtt(self) -> None:
		self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() running")
		try:
			self.logger.info(f"[daemon] MQTT.connect(host='{self.config['mqtt:server']}', port={self.config['mqtt:port']}) for plugin 'brain'")
			async with aiomqtt_Client(self.config['mqtt:server'], self.config['mqtt:port'],
			                          will=aiomqtt_Will('hal9000/event/brain/runlevel', HAL9000_Plugin.RUNLEVEL_KILLED),
			                          identifier='hal9000-brain') as mqtt:
				self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() MQTT.subscribe('hal9000/command/brain/status') for plugin 'brain'")
				await mqtt.subscribe('hal9000/command/brain/status')
				for mqtt_topic, trigger in self.callbacks['mqtt'].items():
					await mqtt.subscribe(mqtt_topic)
					self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() MQTT.subscribe('{mqtt_topic}') for trigger '{str(trigger)}'")
				self.tasks['mqtt:publisher'] = asyncio_create_task(self.task_mqtt_publisher(mqtt))
				self.tasks['mqtt:subscriber'] = asyncio_create_task(self.task_mqtt_subscriber(mqtt))
				try:
					while self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
						await asyncio_sleep(0.1)
				finally:
					await mqtt.publish('hal9000/event/brain/runlevel', 'killed') # aiomqtt's will=... somehow doesn't work
		except asyncio_CancelledError as e:
			self.logger.debug(f"[daemon] task mqtt has been cancelled")
		except Exception as e:
			self.logger.critical(f"[daemon] {str(e)}")
			raise e
		finally:
			self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() exiting")


	async def task_signal(self) -> None:
		self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_signal() running")
		try:
			while self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
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
			self.logger.critical(f"[daemon] Daemon.task_signal(): ({type(e).__name__}) => {str(e)}")
			self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
			raise e
		finally:
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_signal() exiting")


	async def on_scheduler(self, plugin: str, signal: dict) -> None:
		self.queue_signal(plugin, signal)


	def import_plugin(self, plugin_name: str, class_name: str) -> HAL9000_Plugin:
		plugin = importlib_import_module(plugin_name)
		if plugin is not None:
			return getattr(plugin, class_name)
		return None


	def on_plugin_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_value, new_value, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.REMOTE_REQUESTED:
				logging_getLogger().info(f"[daemon] Plugin '{plugin.plugin_id}': {key} is requested to change from '{old_value}' to '{new_value}'")
			case CommitPhase.COMMIT:
				logging_getLogger().info(f"[daemon] Plugin '{plugin.plugin_id}': {key} changes from '{old_value}' to '{new_value}'")
		return True


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				match old_runlevel:
					case HAL9000_Plugin.RUNLEVEL_STARTING:
						if new_runlevel != HAL9000_Plugin.RUNLEVEL_READY:
							self.daemon.logger.info(f"[daemon] inhibiting change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
							return False
					case HAL9000_Plugin.RUNLEVEL_READY:
						if new_runlevel != HAL9000_Plugin.RUNLEVEL_RUNNING:
							self.daemon.logger.info(f"[daemon] inhibiting change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
							return False
					case HAL9000_Plugin.RUNLEVEL_RUNNING:
						self.daemon.logger.info(f"[daemon] inhibiting change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
						return False
			case CommitPhase.COMMIT:
				match new_runlevel:
					case HAL9000_Plugin.RUNLEVEL_READY:
						self.queue_signal('brain', {'runlevel': HAL9000_Plugin.RUNLEVEL_RUNNING})
					case HAL9000_Plugin.RUNLEVEL_RUNNING:
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
				self.logger.debug(f"[daemon] STATUS at runlevel change from '{old_runlevel}' to '{new_runlevel}' = {self.plugins}")
				self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/runlevel', 'payload': new_runlevel})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_status not in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP, Daemon.BRAIN_STATUS_DYING]:
					self.daemon.logger.info(f"[daemon] inhibiting change from status '{old_status}' to '{new_status}'")
					return False
			case CommitPhase.COMMIT:
				self.logger.debug(f"[daemon] STATUS at status change from '{old_status}' to '{new_status}' = {self.plugins}")
				self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/status', 'payload': new_status})
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_time not in [Daemon.BRAIN_TIME_UNSYNCHRONIZED, Daemon.BRAIN_TIME_SYNCHRONIZED]:
					self.daemon.logger.info(f"[daemon] inhibiting change from time '{old_time}' to '{new_time}'")
					return False
			case CommitPhase.COMMIT:
				match new_time:
					case Daemon.BRAIN_TIME_UNSYNCHRONIZED:
						self.create_scheduled_signal(   1, 'brain', {'time:sync': {}}, 'scheduler://brain/time:sync', 'interval')
					case Daemon.BRAIN_TIME_SYNCHRONIZED:
						self.create_scheduled_signal(3600, 'brain', {'time:sync': {}}, 'scheduler://brain/time:sync', 'interval')
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'runlevel' in signal:
			match self.plugins['brain'].runlevel:
				case HAL9000_Plugin.RUNLEVEL_STARTING:
					if signal['runlevel'] == HAL9000_Plugin.RUNLEVEL_READY:
						self.plugins['brain'].runlevel = HAL9000_Plugin.RUNLEVEL_READY
				case HAL9000_Plugin.RUNLEVEL_READY:
					if signal['runlevel'] == HAL9000_Plugin.RUNLEVEL_RUNNING:
						self.plugins['brain'].runlevel = HAL9000_Plugin.RUNLEVEL_RUNNING
				case HAL9000_Plugin.RUNLEVEL_RUNNING:
					self.logger.error(f"[daemon] signal with unexpected new runlevel '{signal['runlevel']}' (current runlevel='running')")
				case other:
					self.logger.error(f"[daemon] unexpected current runlevel '{self.plugins['brain'].runlevel}'")
		if 'status' in signal:
			match self.plugins['brain'].status:
				case Daemon.BRAIN_STATUS_LAUNCHING | Daemon.BRAIN_STATUS_AWAKE | Daemon.BRAIN_STATUS_ASLEEP:
					if signal['status'] in [Daemon.BRAIN_STATUS_AWAKE, Daemon.BRAIN_STATUS_ASLEEP, Daemon.BRAIN_STATUS_DYING]:
						self.plugins['brain'].status = signal['status']
				case Daemon.BRAIN_STATUS_DYING:
					pass
		if 'time:sync' in signal:
			self.plugins['brain'].time = Daemon.BRAIN_TIME_SYNCHRONIZED if os_path_exists('/run/systemd/timesync/synchronized') is True else Daemon.BRAIN_TIME_UNSYNCHRONIZED


	def process_error(self, level: str, id: str, title: str, details: str = '<no details>') -> None:
		self.logger.log(getattr(logging, level.upper()), f"[daemon] ERROR #{id}: {title} => {details}")
		if self.plugins['brain'].runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING and self.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
			url = self.substitute_vars(self.config['help:error-url'], {'error_id': id})
			self.queue_signal('*', {'error': {'id': id, 'url': url, 'title': title, 'details': details}})


	async def signal(self, plugin: str, signal: dict) -> None:
		if plugin in self.plugins:
			await self.plugins[plugin].signal(signal)


	def queue_signal(self, plugin: str, signal: dict) -> None:
		self.signal_queue.put_nowait({'plugin': plugin, 'signal': signal})


	def create_scheduled_signal(self, seconds: float, plugin: str, signal: dict, id: str | None = None, mode: str = 'single') -> None:
		match mode:
			case 'single':
				run_date = datetime_datetime.now() + datetime_timedelta(seconds=int(seconds), microseconds=int((seconds - int(seconds)) * 1000000))
				self.scheduler.add_job(self.on_scheduler, 'date', run_date=run_date, args=[plugin, signal], id=id, name=id, replace_existing=True)
			case 'interval':
				self.scheduler.add_job(self.on_scheduler, 'interval', seconds=int(seconds), args=[plugin, signal], id=id, name=id, replace_existing=True)
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
		self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING


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

