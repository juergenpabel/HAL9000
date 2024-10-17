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
import logging
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

from .plugin import HAL9000_Plugin, HAL9000_Plugin_Data, DataInvalid, RUNLEVEL, CommitPhase


class BRAIN_STATUS(enum_StrEnum):
	LAUNCHING = 'launching'
	AWAKE     = 'awake'
	ASLEEP    = 'asleep'
	DYING     = 'dying'


class Brain(object):
	LOGLEVEL_TRACE = 5
	TIME_UNSYNCHRONIZED = 'unsynchronized'
	TIME_SYNCHRONIZED =   'synchronized'

	def __init__(self) -> None:
		self.name = 'daemon:brain:default'
		self.logger = logging_getLogger()
		self.config = {}
		self.plugins = {}
		self.plugins['brain'] = HAL9000_Plugin_Data('brain', daemon=self, runlevel=RUNLEVEL.STARTING, status=BRAIN_STATUS.LAUNCHING)
		self.plugins['brain'].addLocalNames(['time'])
		self.tasks = {}
		self.actions = {}
		self.triggers = {}
		self.callbacks = {'mqtt': {}}
		self.runlevel_inhibitors = {RUNLEVEL.STARTING: {}, RUNLEVEL.READY: {}, RUNLEVEL.RUNNING: {}}
		self.add_runlevel_inhibitor(RUNLEVEL.STARTING, 'plugins:runlevel', self.runlevel_inhibitor_starting_plugins)
		self.add_runlevel_inhibitor(RUNLEVEL.READY,    'brain:time',       self.runlevel_inhibitor_ready_time)
		self.signal_queue = asyncio_Queue()
		self.mqtt_publish_queue = asyncio_Queue()
		self.scheduler = apscheduler_schedulers_AsyncIOScheduler()
		signal_signal(signal_SIGHUP, self.on_posix_signal)
		signal_signal(signal_SIGTERM, self.on_posix_signal)
		signal_signal(signal_SIGQUIT, self.on_posix_signal)
		signal_signal(signal_SIGINT, self.on_posix_signal)


	def configure(self, filename: str) -> None:
		logging_addLevelName(Brain.LOGLEVEL_TRACE, 'TRACE')
		logging_config_fileConfig(filename)
		logging_getLogger('apscheduler').setLevel('ERROR')
		self.logger.info(f"[brain] LOADING CONFIGURATION '{filename}'")
		self.logger.info(f"[brain] Log-level set to '{logging_getLevelName(self.logger.level)}'")
		self.configuration = configparser_ConfigParser(delimiters='=',
		                                               converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
		                                                           'string': lambda string: string.strip('"').strip("'")}, interpolation=None)
		self.configuration.read(filename)
		self.config['mqtt:server']       = str(os_getenv('MQTT_SERVER', default=self.configuration.getstring('mqtt', 'server', fallback='127.0.0.1')))
		self.config['mqtt:port']         = int(os_getenv('MQTT_PORT', default=self.configuration.getint('mqtt', 'port', fallback=1883)))
		self.config['help:error-url'] = self.configuration.getstring('help', 'error-url', fallback='https://github.com/juergenpabel/HAL9000/wiki/Error-database')
		self.config['help:splash-url'] = self.configuration.getstring('help', 'splash-url', fallback='https://github.com/juergenpabel/HAL9000/wiki/Splashs')
		for section_name in self.configuration.sections():
			plugin_path = self.configuration.getstring(section_name, 'plugin', fallback=None)
			plugin_hidden = self.configuration.getboolean(section_name, 'hidden', fallback=False)
			if plugin_path is not None:
				module = importlib_import_module(plugin_path)
				if module is not None:
					plugin_type, plugin_id = section_name.lower().split(':',1)
					match plugin_type.lower():
						case 'action':
							Action = getattr(module, 'Action')
							if Action is not None:
								self.actions[plugin_id] = Action(plugin_id, HAL9000_Plugin_Data(plugin_id, daemon=self, hidden=plugin_hidden), daemon=self)
						case 'trigger':
							Trigger = getattr(module, 'Trigger')
							if Trigger is not None:
								self.triggers[plugin_id] = Trigger(plugin_id, HAL9000_Plugin_Data(plugin_id, daemon=self, hidden=plugin_hidden))
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
		self.logger.debug(f"[brain] Brain starting...")
		results = await self.runlevel_starting()
		if len(results) == 0 and self.plugins['brain'].status != BRAIN_STATUS.DYING:
			results = await self.runlevel_ready()
		if len(results) == 0 and self.plugins['brain'].status != BRAIN_STATUS.DYING:
			results = await self.runlevel_running()
		self.logger.debug(f"[brain] gathering tasks and exiting...")
		for name, task in self.tasks.copy().items():
			self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.loop() cancelling and gathering task '{name}'...")
			task.cancel()
			results[name] = (await asyncio_gather(task, return_exceptions=True)).pop()
		self.scheduler.shutdown()
		return results


	async def runlevel_starting(self) -> dict:
		self.logger.info(f"[brain] Startup: {RUNLEVEL.STARTING}")
		self.logger.debug(f"[brain] STATUS at runlevel '{self.plugins['brain'].runlevel}' = { {k: v for k,v in self.plugins.items() if v.hidden is False} }")
		self.plugins['brain'].addSignalHandler(self.on_brain_signal)
		self.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.plugins['brain'].addNameCallback(self.on_plugin_callback, '*')
		for plugin in self.plugins.values():
			plugin.addNameCallback(self.on_plugin_callback, '*')
		try:
			self.scheduler.start()
			self.tasks['signals'] = asyncio_create_task(self.task_signal())
			self.tasks['mqtt'] = asyncio_create_task(self.task_mqtt())
			while 'mqtt:publisher' not in self.tasks and 'mqtt:subscriber' not in self.tasks:
				await asyncio_sleep(0.1)
			self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/runlevel', 'payload': 'starting'})
			self.logger.info(f"[brain] Connected to MQTT, now requesting runlevel announcements from these services:")
			for name, plugin in dict(filter(lambda item: item[1].runlevel == DataInvalid.UNKNOWN, self.plugins.items())).items():
				self.logger.info(f"[brain] - Service '{name}'")
				self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/command/{name}/runlevel', 'payload': None})
			self.logger.info(f"[brain] Waiting for these services to announce their runlevel...")
			while len(list(filter(lambda plugin: plugin.runlevel == DataInvalid.UNKNOWN, self.plugins.values()))) > 0:
				if self.plugins['brain'].status == BRAIN_STATUS.DYING:
					self.logger.debug(f"[brain] status changed to 'dying', raising exception while waiting for plugins in runlevel 'starting'")
					raise RuntimeError(BRAIN_STATUS.DYING)
				await asyncio_sleep(0.1)
			self.logger.info(f"[brain] ...all services announced their runlevel")
			self.logger.debug(f"[brain] Inhibitors in runlevel '{RUNLEVEL.STARTING}': " \
			                  f"{', '.join(list(self.runlevel_inhibitors[RUNLEVEL.STARTING].keys()))}...")
			self.logger.info(f"[brain] Waiting for runlevel inhibitors to finish...")
			while len(self.runlevel_inhibitors[RUNLEVEL.STARTING]) > 0:
				self.evaluate_runlevel_inhibitors(RUNLEVEL.STARTING)
				if self.plugins['brain'].status == BRAIN_STATUS.DYING:
					self.logger.debug(f"[brain] status changed to 'dying', raising exception while waiting for inhibitors in runlevel 'starting'")
					raise RuntimeError(BRAIN_STATUS.DYING)
				await asyncio_sleep(0.1)
			self.logger.info(f"[brain] ...all inhibitors in runlevel '{RUNLEVEL.STARTING}' have finished")
			self.logger.debug(f"[brain] STATUS after runlevel 'starting' = { {k: v for k,v in self.plugins.items() if v.hidden is False} }")
		except Exception as e:
			self.logger.debug(f"[brain] execution of runlevel 'starting' aborted, services that haven't announced their runlevel: " \
			                  f"{', '.join(list(dict(filter(lambda item: item[1].runlevel == DataInvalid.UNKNOWN, self.plugins.items())).keys()))}")
			self.logger.debug(f"[brain] execution of runlevel 'starting' aborted, remaining inhibitors that haven't finished: " \
			                  f"{', '.join(list(self.runlevel_inhibitors[RUNLEVEL.STARTING].keys()))}")
			self.logger.critical(f"[brain] Brain.runlevel_starting(): {type(e).__name__} => {str(e)}")
			from traceback import format_exc as traceback_format_exc
			self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] {traceback_format_exc()}")
			if str(e) != BRAIN_STATUS.DYING:
				self.plugins['brain'].status = BRAIN_STATUS.DYING
				return {'main': e}
		self.plugins['brain'].runlevel = RUNLEVEL.READY, CommitPhase.COMMIT
		return {}

			
	async def runlevel_ready(self) -> dict:
		self.logger.info(f"[brain] Startup: {RUNLEVEL.READY}")
		self.logger.debug(f"[brain] STATUS in runlevel '{self.plugins['brain'].runlevel}' = { {k: v for k,v in self.plugins.items() if v.hidden is False} }")
		try:
			self.plugins['brain'].status = BRAIN_STATUS.AWAKE
			self.queue_signal('brain', {'time:sync': {}})
			self.logger.debug(f"[brain] Inhibitors in runlevel '{RUNLEVEL.READY}': " \
			                  f"{', '.join(list(self.runlevel_inhibitors[RUNLEVEL.READY].keys()))}...")
			self.logger.info(f"[brain] Waiting for runlevel inhibitors to finish...")
			while len(self.runlevel_inhibitors[RUNLEVEL.READY]) > 0:
				if self.plugins['brain'].status == BRAIN_STATUS.DYING:
					self.logger.debug(f"[brain] status changed to 'dying', raising exception while waiting for inhibitos in runlevel 'ready'")
					raise RuntimeError(BRAIN_STATUS.DYING)
				self.evaluate_runlevel_inhibitors(RUNLEVEL.READY)
				await asyncio_sleep(0.1)
			self.logger.info(f"[brain] ...all inhibitors in runlevel '{RUNLEVEL.READY}' have finished")
			self.logger.debug(f"[brain] STATUS after runlevel 'ready' = { {k: v for k,v in self.plugins.items() if v.hidden is False} }")
		except Exception as e:
			self.logger.debug(f"[brain] execution of runlevel 'ready' aborted, remaining inhibitors that haven't completed at runtime: " \
			                  f"{', '.join(list(self.runlevel_inhibitors[RUNLEVEL.READY].keys()))}")
			self.logger.critical(f"[brain] Brain.runlevel_ready(): {type(e).__name__} => {str(e)}")
			from traceback import format_exc as traceback_format_exc
			self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] {traceback_format_exc()}")
			if str(e) != BRAIN_STATUS.DYING:
				self.plugins['brain'].status = BRAIN_STATUS.DYING
				return {'main': e}
		self.plugins['brain'].runlevel = RUNLEVEL.RUNNING, CommitPhase.COMMIT
		return {}


	async def runlevel_running(self) -> dict:
		self.logger.info(f"[brain] Startup: {RUNLEVEL.RUNNING}")
		self.logger.debug(f"[brain] STATUS in runlevel '{self.plugins['brain'].runlevel}' = { {k: v for k,v in self.plugins.items() if v.hidden is False} }")
		try:
			while self.plugins['brain'].runlevel == RUNLEVEL.RUNNING and self.plugins['brain'].status != BRAIN_STATUS.DYING:
				await asyncio_sleep(0.1)
			self.logger.debug(f"[brain] STATUS after runlevel '{self.plugins['brain'].runlevel}' = { {k: v for k,v in self.plugins.items() if v.hidden is False} }")
		except Exception as e:
			self.logger.critical(f"[brain] Brain.runlevel_running(): {type(e).__name__} => {str(e)}")
			from traceback import format_exc as traceback_format_exc
			self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] {traceback_format_exc()}")
			if str(e) != BRAIN_STATUS.DYING:
				self.plugins['brain'].status = BRAIN_STATUS.DYING
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
				self.logger.debug(f"[brain] Inhibitor '{name}' has finished")
				del self.runlevel_inhibitors[runlevel][name]


	def runlevel_inhibitor_starting_plugins(self) -> bool:
		for name, plugin in self.plugins.items():
			if name != 'brain' and plugin.runlevel != RUNLEVEL.RUNNING:
				return False
		return True


	def runlevel_inhibitor_ready_time(self) -> bool:
		if self.plugins['brain'].time in list(DataInvalid):
			return False
		return True


	async def task_mqtt_subscriber(self, mqtt: aiomqtt_Client) -> None:
		self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt_subscriber() running")
		try:
			async for message in mqtt.messages:
				topic = message.topic.value
				payload = message.payload.decode('utf-8', 'surrogateescape')
				self.logger.debug(f"[brain] MQTT received: {topic} => {str(chr(0x27))+str(chr(0x27)) if payload == '' else payload}")
				match topic:
					case 'hal9000/command/brain/status':
						if self.plugins['brain'].status in [BRAIN_STATUS.AWAKE, BRAIN_STATUS.ASLEEP]:
							if payload in [BRAIN_STATUS.AWAKE, BRAIN_STATUS.ASLEEP, BRAIN_STATUS.DYING]:
								self.plugins['brain'].status = payload
					case other:
						signals = {}
						if topic in self.callbacks['mqtt']:
							triggers = self.callbacks['mqtt'][topic]
							if self.plugins['brain'].status == BRAIN_STATUS.ASLEEP:
								triggers = [trigger for trigger in triggers if trigger.sleepless is True]
							self.logger.debug(f"[brain] TRIGGERS: {','.join(str(x) for x in triggers)}")
							self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt_subscriber() STATUS before triggers = {self.plugins}")
							for trigger in triggers:
								signal = trigger.handle(message)
								if signal is not None and len(signal) > 0:
									signals[str(trigger)] = signal
						self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt_subscriber() SIGNALS generated by TRIGGERS: {signals}")
						for trigger_id, signal in signals.items():
							plugin_name = signal[0]
							signal = signal[1]
							if plugin_name not in self.plugins:
								self.logger.warning(f"[brain] SIGNAL for unknown plugin '{plugin_name}' " \
								                    f"generated by trigger '{trigger_id}: '{signal}'")
							else:
								self.logger.debug(f"[brain] SIGNAL for plugin '{plugin_name}' " \
								                  f"generated by trigger '{trigger_id}': '{signal}'")
								await self.plugins[plugin_name].signal(signal)
						self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt_subscriber() STATUS after signals   = {self.plugins}")
		except asyncio_CancelledError as e:
			pass
		except Exception as e:
			if self.tasks['mqtt'].cancelled() is False and self.plugins['brain'].status != BRAIN_STATUS.DYING:
				self.logger.critical(f"[brain] task 'mqtt_subscriber' exiting due to : {type(e).__name__} => {str(e)}")
				raise e
		finally:
			self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt_subscriber() exiting")
			self.plugins['brain'].status = BRAIN_STATUS.DYING


	async def task_mqtt_publisher(self, mqtt: aiomqtt_Client) -> None:
		self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt_publisher() running")
		try:
			while self.plugins['brain'].status != BRAIN_STATUS.DYING:
				if self.mqtt_publish_queue.empty() is False:
					data = await self.mqtt_publish_queue.get()
					if isinstance(data, dict) is True and 'topic' in data and 'payload' in data:
						topic = data['topic']
						payload = data['payload']
						if isinstance(payload, dict) is True:
							payload = json_dumps(payload)
						await mqtt.publish(topic, payload)
						self.logger.debug(f"[brain] MQTT published: {topic} => {str(chr(0x27))+str(chr(0x27)) if payload == '' else payload}")
				await asyncio_sleep(0.01)
		except asyncio_CancelledError as e:
			pass
		finally:
			self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt_publisher() exiting")
			self.plugins['brain'].status = BRAIN_STATUS.DYING


	async def task_mqtt(self) -> None:
		self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt() running")
		try:
			self.logger.info(f"[brain] MQTT.connect(host='{self.config['mqtt:server']}', port={self.config['mqtt:port']}) for plugin 'brain'")
			async with aiomqtt_Client(self.config['mqtt:server'], self.config['mqtt:port'],
			                          will=aiomqtt_Will('hal9000/event/brain/runlevel', RUNLEVEL.KILLED),
			                          identifier='hal9000-brain') as mqtt:
				self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt() MQTT.subscribe('hal9000/command/brain/status') for plugin 'brain'")
				await mqtt.subscribe('hal9000/command/brain/status')
				for mqtt_topic, trigger in self.callbacks['mqtt'].items():
					await mqtt.subscribe(mqtt_topic)
					self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt() MQTT.subscribe('{mqtt_topic}') for trigger '{str(trigger)}'")
				self.tasks['mqtt:publisher'] = asyncio_create_task(self.task_mqtt_publisher(mqtt))
				self.tasks['mqtt:subscriber'] = asyncio_create_task(self.task_mqtt_subscriber(mqtt))
				try:
					while self.plugins['brain'].status != BRAIN_STATUS.DYING:
						await asyncio_sleep(0.1)
				finally:
					await mqtt.publish('hal9000/event/brain/runlevel', 'killed') # aiomqtt's will=... somehow doesn't work
		except asyncio_CancelledError as e:
			self.logger.debug(f"[brain] task mqtt has been cancelled")
		except Exception as e:
			self.logger.critical(f"[brain] {str(e)}")
			raise e
		finally:
			self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_mqtt() exiting")
			self.plugins['brain'].status = BRAIN_STATUS.DYING


	async def task_signal(self) -> None:
		self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_signal() running")
		try:
			while self.plugins['brain'].status != BRAIN_STATUS.DYING:
				if self.signal_queue.empty() is False:
					data = await self.signal_queue.get()
					if isinstance(data, dict) is True and 'plugin' in data and 'signal' in data:
						plugin = data['plugin']
						signal = data['signal']
						self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_signal() SIGNAL for plugin '{plugin}': '{signal}'")
						if plugin == '*':
							for plugin in self.plugins.values():
								await plugin.signal(signal)
						elif plugin in self.plugins:
							await self.plugins[plugin].signal(signal)
						else:
							self.logger.warning(f"[brain] Ignoring SIGNAL for unknown plugin '{plugin}' - ignoring it (=> BUG)")
					else:
						self.logger.warning(f"[brain] Ignoring invalid SIGNAL '{str(signal)}' from signal_queue")
				await asyncio_sleep(0.01)
		except asyncio_CancelledError as e:
			self.signal_queue = None
		except Exception as e:
			self.plugins['brain'].status = BRAIN_STATUS.DYING
			self.logger.critical(f"[brain] Brain.task_signal(): {type(e).__name__} => {str(e)}")
			from traceback import format_exc as traceback_format_exc
			self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] {traceback_format_exc()}")
			raise e
		finally:
			self.logger.log(Brain.LOGLEVEL_TRACE, f"[brain] Brain.task_signal() exiting")
			self.plugins['brain'].status = BRAIN_STATUS.DYING


	async def on_scheduler(self, plugin: str, signal: dict) -> None:
		self.queue_signal(plugin, signal)


	def import_plugin(self, plugin_name: str, class_name: str) -> HAL9000_Plugin:
		plugin = importlib_import_module(plugin_name)
		if plugin is not None:
			return getattr(plugin, class_name)
		return None


	def on_plugin_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_value, new_value, phase: CommitPhase) -> bool:
		log_function = logging_getLogger().info
		match self.plugins['brain'].runlevel:
			case RUNLEVEL.STARTING:
				log_function = logging_getLogger().debug
			case RUNLEVEL.READY:
				log_function = logging_getLogger().debug
			case RUNLEVEL.RUNNING:
				if plugin.hidden is True:
					log_function = logging_getLogger().debug
		match phase:
			case CommitPhase.REMOTE_REQUESTED:
				log_function(f"[brain] Plugin '{plugin.name}': {key} is requested to change from '{old_value}' to '{new_value}'")
			case CommitPhase.COMMIT:
				log_function(f"[brain] Plugin '{plugin.name}': {key} changes from '{old_value}' to '{new_value}'")
		return True


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				match old_runlevel:
					case RUNLEVEL.STARTING:
						if new_runlevel != RUNLEVEL.READY:
							self.logger.info(f"[brain] preventing (invalid) change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
							return False
					case RUNLEVEL.READY:
						if new_runlevel != RUNLEVEL.RUNNING:
							self.logger.info(f"[brain] preventing (invalid) change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
							return False
					case RUNLEVEL.RUNNING:
						self.logger.info(f"[brain] preventing (invalid) change of runlevel from '{old_runlevel}' to '{new_runlevel}'")
						return False
			case CommitPhase.COMMIT:
				self.logger.debug(f"[brain] STATUS at runlevel change from '{old_runlevel}' to '{new_runlevel}' = { {k: v for k,v in self.plugins.items() if v.hidden is False} }")
				self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/runlevel', 'payload': new_runlevel})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_status: str, new_status: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_status not in [BRAIN_STATUS.AWAKE, BRAIN_STATUS.ASLEEP, BRAIN_STATUS.DYING]:
					self.logger.info(f"[brain] inhibiting change from status '{old_status}' to '{new_status}'")
					return False
			case CommitPhase.COMMIT:
				self.logger.debug(f"[brain] STATUS at status change from '{old_status}' to '{new_status}' = { {k: v for k,v in self.plugins.items() if v.hidden is False} }")
				self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/status', 'payload': new_status})
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_time: str, new_time: str, phase: CommitPhase) -> bool:
		match phase:
			case CommitPhase.LOCAL_REQUESTED:
				if new_time not in [Brain.TIME_UNSYNCHRONIZED, Brain.TIME_SYNCHRONIZED]:
					self.logger.info(f"[brain] inhibiting change from time '{old_time}' to '{new_time}'")
					return False
			case CommitPhase.COMMIT:
				match new_time:
					case Brain.TIME_UNSYNCHRONIZED:
						self.create_scheduled_signal(   1, 'brain', {'time:sync': {}}, 'scheduler://brain/time:sync', 'interval')
					case Brain.TIME_SYNCHRONIZED:
						self.create_scheduled_signal(3600, 'brain', {'time:sync': {}}, 'scheduler://brain/time:sync', 'interval')
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'runlevel' in signal:
			match self.plugins['brain'].runlevel:
				case RUNLEVEL.STARTING:
					if signal['runlevel'] == RUNLEVEL.READY:
						self.plugins['brain'].runlevel = RUNLEVEL.READY
				case RUNLEVEL.READY:
					if signal['runlevel'] == RUNLEVEL.RUNNING:
						self.plugins['brain'].runlevel = RUNLEVEL.RUNNING
				case RUNLEVEL.RUNNING:
					self.logger.error(f"[brain] signal with unexpected new runlevel '{signal['runlevel']}' (current runlevel='running')")
				case other:
					self.logger.error(f"[brain] unexpected current runlevel '{self.plugins['brain'].runlevel}'")
		if 'status' in signal:
			match self.plugins['brain'].status:
				case BRAIN_STATUS.LAUNCHING | BRAIN_STATUS.AWAKE | BRAIN_STATUS.ASLEEP:
					if signal['status'] in [BRAIN_STATUS.AWAKE, BRAIN_STATUS.ASLEEP, BRAIN_STATUS.DYING]:
						self.plugins['brain'].status = signal['status']
				case BRAIN_STATUS.DYING:
					pass
		if 'time:sync' in signal:
			self.plugins['brain'].time = Brain.TIME_SYNCHRONIZED if os_path_exists('/run/systemd/timesync/synchronized') is True else Brain.TIME_UNSYNCHRONIZED


	def process_error(self, level: str, id: str, title: str, details: str = '<no details>') -> None:
		self.logger.log(getattr(logging, level.upper()), f"[brain] ERROR #{id}: {title} => {details}")
		if self.plugins['brain'].runlevel == RUNLEVEL.RUNNING and self.plugins['brain'].status == BRAIN_STATUS.AWAKE:
			url = self.substitute_vars(self.config['help:error-url'], {'error_id': id})
			self.queue_signal('*', {'error': {'id': id, 'url': url, 'title': title, 'details': details}})


	def queue_signal(self, plugin: str, signal: dict) -> None:
		if self.logger.isEnabledFor(Brain.LOGLEVEL_TRACE) is True:
			self.add_caller_trace(signal)
		self.signal_queue.put_nowait({'plugin': plugin, 'signal': signal})


	def create_scheduled_signal(self, seconds: float, plugin: str, signal: dict, id: str | None = None, mode: str = 'single') -> None:
		if self.logger.isEnabledFor(Brain.LOGLEVEL_TRACE) is True:
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
				logging_getLogger().error(f"unsupported schedule mode '{mode}' in Brain.create_scheduled_signal()")


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
		self.plugins['brain'].status = BRAIN_STATUS.DYING


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
					caller = f"{fi.frame.f_locals['self'].name}<{fi.function}>"
				signal['trace'] = caller
				if trace_notice != '':
					signal['trace'] += f' ({trace_notice})'
			del stack # cycle breaking for GC

