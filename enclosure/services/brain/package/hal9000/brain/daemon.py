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


from .plugin import HAL9000_Plugin, HAL9000_Plugin_Status


class Daemon(object):

	BRAIN_STATUS_AWAKE = 'awake'
	BRAIN_STATUS_ASLEEP = 'asleep'
	BRAIN_STATUS_DYING = 'dying'

	LOGLEVEL_TRACE = 5

	def __init__(self) -> None:
		self.logger = logging_getLogger()
		self.config = {}
		self.plugins = {}
		self.plugins['brain'] = HAL9000_Plugin_Status('brain', runlevel=HAL9000_Plugin.RUNLEVEL_STARTING)
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
		self.config['startup:init-timeout'] = self.configuration.getint('startup', 'init-timeout', fallback=10)
		self.config['mqtt:server']       = str(os_getenv('MQTT_SERVER', default=self.configuration.getstring('mqtt', 'server', fallback='127.0.0.1')))
		self.config['mqtt:port']         = int(os_getenv('MQTT_PORT', default=self.configuration.getint('mqtt', 'port', fallback=1883)))
		self.config['brain:require-synced-time'] = self.configuration.getboolean('brain', 'require-synced-time', fallback=True)
		self.config['brain:sleep-time']  = self.configuration.get('brain', 'sleep-time', fallback=None)
		self.config['brain:wakeup-time'] = self.configuration.get('brain', 'wakeup-time', fallback=None)
		self.config['help:error-url'] = self.configuration.getstring('help', 'error-url', fallback='https://github.com/juergenpabel/HAL9000/wiki/Error-database')
		self.config['help:splash-url'] = self.configuration.getstring('help', 'splash-url', fallback='https://github.com/juergenpabel/HAL9000/wiki/Splashs')
		self.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.plugins['brain'].addNameCallback(self.on_brain_status_callback, 'status')
		self.plugins['brain'].addNameCallback(self.on_brain_time_callback, 'time')
		self.plugins['brain'].addSignalHandler(self.on_brain_signal)
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
							self.callbacks['mqtt'][mqtt_topic] = []
						self.callbacks['mqtt'][mqtt_topic].append(trigger)


	async def loop(self) -> dict:
		results = {'main': None}
		try:
			self.scheduler.start()
			self.tasks['signals'] = asyncio_create_task(self.task_signal())
			self.tasks['mqtt'] = asyncio_create_task(self.task_mqtt())
			while 'mqtt:publisher' not in self.tasks and 'mqtt:subscriber' not in self.tasks:
				await asyncio_sleep(0.1)
			self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/runlevel', 'payload': 'starting'})
			startup_timeout = time_monotonic() + self.config['startup:init-timeout']
			plugins = { HAL9000_Plugin_Status.STATUS_UNINITIALIZED: {},
			            HAL9000_Plugin.RUNLEVEL_UNKNOWN: {},
			            HAL9000_Plugin.RUNLEVEL_STARTING: {},
			            HAL9000_Plugin.RUNLEVEL_READY: {},
			            HAL9000_Plugin.RUNLEVEL_RUNNING: {},
			            HAL9000_Plugin.RUNLEVEL_KILLED: {} }
			for plugin in list(self.triggers.values()) + list(self.actions.values()):
				plugin_id = str(plugin)
				plugin_runlevel = plugin.runlevel()
				plugins[plugin_runlevel][plugin_id] = plugin
			self.logger.info(f"[daemon] Startup initialized (plugins that need runtime registration):")
			for plugin_id, plugin in plugins[HAL9000_Plugin.RUNLEVEL_UNKNOWN].items():
				plugin_name = plugin_id.split(':').pop()
				self.logger.info(f"[daemon]  - Plugin '{plugin_name}'")
				self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/command/{plugin_name}/runlevel', 'payload': ''})
			self.logger.debug(f"[daemon] STATUS at startup = {self.plugins}")
			while self.plugins['brain'].runlevel == HAL9000_Plugin.RUNLEVEL_STARTING and self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
				for runlevel in [HAL9000_Plugin.RUNLEVEL_UNKNOWN, HAL9000_Plugin.RUNLEVEL_STARTING]:
					if runlevel in plugins:
						for id, plugin in plugins[runlevel].items():
							plugin_runlevel = plugin.runlevel()
							if plugin_runlevel != runlevel:
								self.logger.info(f"[daemon] Plugin '{id.split(':').pop()}' is now in runlevel '{plugin_runlevel}'")
								plugins[runlevel][id] = None
								plugins[plugin_runlevel][id] = plugin
						plugins[runlevel] = {id:plugin for id,plugin in plugins[runlevel].items() if plugin is not None}
				if startup_timeout is not None:
					if time_monotonic() > startup_timeout:
						self.logger.critical(f"[daemon] Startup failed (plugins that haven't reported their runlevel):")
						for id, plugin in plugins[HAL9000_Plugin.RUNLEVEL_UNKNOWN].items():
							error = plugin.runlevel_error()
							self.process_error('critical', error['id'], f"    Plugin '{id.split(':').pop()}'", error['message'])
						self.logger.debug(f"[daemon] STATUS at startup-timeout = {self.plugins}")
						self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
					if len(plugins[HAL9000_Plugin.RUNLEVEL_UNKNOWN]) == 0:
						self.logger.info(f"[daemon] Startup in progress for all plugins")
						startup_timeout = None
						del plugins[HAL9000_Plugin.RUNLEVEL_UNKNOWN]
						for plugin in self.plugins.values():
							plugin.addNameCallback(self.on_plugin_callback, '*')
				if startup_timeout is None:
					if HAL9000_Plugin.RUNLEVEL_STARTING in plugins:
						if len(plugins[HAL9000_Plugin.RUNLEVEL_STARTING]) == 0:
							del plugins[HAL9000_Plugin.RUNLEVEL_STARTING]
							self.logger.info(f"[daemon] Startup completed for all plugins")
							self.plugins['brain'].runlevel = HAL9000_Plugin.RUNLEVEL_READY
				await asyncio_sleep(0.1)
			if self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
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
				self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.loop() running...")
				while self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
					await asyncio_sleep(0.1)
				self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.loop() ...dying")
		except Exception as e:
			self.logger.debug(f"[daemon] {e}")
			self.plugins['brain'].status = Daemon.BRAIN_STATUS_DYING
			results['main'] = e
		self.logger.debug(f"[daemon] cancelling and gathering tasks...")
		for name, task in self.tasks.copy().items():
			self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.loop() cancelling and gathering task '{name}'...")
			task.cancel()
			results[name] = (await asyncio_gather(task, return_exceptions=True)).pop()
		return results
			

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
									trigger_id = str(trigger).split(':', 2)[2]
									signals[trigger_id] = signal
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
			async with aiomqtt_Client(self.config['mqtt:server'], self.config['mqtt:port'], will=aiomqtt_Will('hal9000/event/brain/runlevel', 'killed'), identifier='hal9000-brain') as mqtt:
				try:
					self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() MQTT.subscribe('hal9000/command/brain/status') for plugin 'brain'")
					await mqtt.subscribe('hal9000/command/brain/status')
					for mqtt_topic, trigger in self.callbacks['mqtt'].items():
						await mqtt.subscribe(mqtt_topic)
						self.logger.log(Daemon.LOGLEVEL_TRACE, f"[daemon] Daemon.task_mqtt() MQTT.subscribe('{mqtt_topic}') for trigger '{str(trigger)}'")
					self.tasks['mqtt:publisher'] = asyncio_create_task(self.task_mqtt_publisher(mqtt))
					self.tasks['mqtt:subscriber'] = asyncio_create_task(self.task_mqtt_subscriber(mqtt))
					while self.plugins['brain'].status != Daemon.BRAIN_STATUS_DYING:
						await asyncio_sleep(0.1)
				finally:
					await mqtt.publish('hal9000/event/brain/runlevel', 'killed')
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
						if plugin in self.plugins:
							plugin = self.plugins[plugin]
							await plugin.signal(signal)
						else:
							self.logger.warning(f"[daemon] Ignoring SIGNAL for unknown plugin '{plugin}' - ignoring it (=> BUG)")
					else:
						self.logger.warning(f"[daemon] Ignoring invalid SIGNAL '{str(signal)}' from signal_queue")
				await asyncio_sleep(0.01)
		except asyncio_CancelledError as e:
			self.signal_queue = None
		except Exception as e:
			self.logger.critical(f"[daemon] Daemon.task_signal(): {str(e)}")
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


	def on_plugin_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_value, new_value, pending: bool) -> bool:
		if pending is False:
			if plugin.plugin_id == 'brain' and key == 'runlevel':
				if new_value not in [HAL9000_Plugin.RUNLEVEL_STARTING, \
				                     HAL9000_Plugin.RUNLEVEL_READY, \
				                     HAL9000_Plugin.RUNLEVEL_RUNNING]:
					return False
			if plugin.plugin_id == 'brain' and key == 'status':
				if new_value not in [Daemon.BRAIN_STATUS_AWAKE, \
				                     Daemon.BRAIN_STATUS_ASLEEP, \
				                     Daemon.BRAIN_STATUS_DYING]:
					return False
			logging_getLogger().info(f"[daemon] Plugin '{plugin.plugin_id}': {key} changes from '{old_value}' to '{new_value}'")
		else:
			logging_getLogger().info(f"[daemon] Plugin '{plugin.plugin_id}': {key} is requested to change from '{old_value}' to '{new_value}'")
		return True


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_runlevel: str, new_runlevel: str, pending: bool) -> bool:
		if pending is False:
			self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/runlevel', 'payload': new_runlevel})
			if new_runlevel == HAL9000_Plugin.RUNLEVEL_READY:
				self.queue_signal('brain', {'time:sync': {}})
		return True


	def on_brain_status_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_status: str, new_status: str, pending: bool) -> bool:
		if pending is False:
			self.mqtt_publish_queue.put_nowait({'topic': f'hal9000/event/brain/status', 'payload': new_status})
		return True


	def on_brain_time_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_time: str, new_time: str, pending: bool) -> bool:
		if pending is False:
			if (new_time == 'unsynchronized' and self.config['brain:require-synced-time'] is False) or (new_time == 'synchronized'):
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
				self.plugins['brain'].status = next_brain_status
				if self.plugins['brain'].runlevel == HAL9000_Plugin.RUNLEVEL_READY:
					self.queue_signal('brain', {'runlevel': HAL9000_Plugin.RUNLEVEL_RUNNING})
			match new_time:
				case 'unsynchronized':
					if self.config['brain:require-synced-time'] is True:
						logging_getLogger().info(f"Waiting for system time to become synchronized... (require-synced-time=true)")
					self.schedule_signal(1, 'brain', {'time:sync': {}}, 'brain:time:sync', 'interval')
				case 'synchronized':
					self.remove_scheduled_signal('brain:time:sync')
				case other:
					return False
		return True


	async def on_brain_signal(self, plugin: HAL9000_Plugin_Status, signal: dict) -> None:
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
				case HAL9000_Plugin_Status.STATUS_UNINITIALIZED | Daemon.BRAIN_STATUS_AWAKE | Daemon.BRAIN_STATUS_ASLEEP:
					if signal['status'] in [Daemon.BRAIN_STATUS_AWAKE, \
					                           Daemon.BRAIN_STATUS_ASLEEP,\
					                           Daemon.BRAIN_STATUS_DYING]:
						self.plugins['brain'].status = signal['status']
				case Daemon.BRAIN_STATUS_DYING:
					pass
		if 'error' in signal:
			error = {'level': 'error', 'id': '00', 'title': 'UNEXPECTED ERROR', 'details': ''}
			for field in error.keys():
				if field in signal['error']:
					error[field] = signal['error'][field]
			self.process_error(signal['error']['level'], signal['error']['id'], signal['error']['title'], signal['error']['details'])
		if 'time:sync' in signal:
			time_synchronized = os_path_exists('/run/systemd/timesync/synchronized')
			self.plugins['brain'].time = 'synchronized' if time_synchronized is True else 'unsynchronized'


	def process_error(self, level: str, id: str, title: str, details: str='<no details>') -> None:
		self.logger.log(getattr(logging, level.upper()), f"[daemon] ERROR #{id}: {title} => {details}")
		if self.plugins['brain'].runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING and self.plugins['brain'].status == Daemon.BRAIN_STATUS_AWAKE:
			self.queue_signal('frontend', {'gui': {'screen': {'name': 'error', 'parameter': {'id': id, 'url': self.config['help:error-url'].format(error_id=id), 'message': title}}}}) #TODO: non-frontend


	async def signal(self, plugin: str, signal: dict) -> None:
		if plugin in self.plugins:
			await self.plugins[plugin].signal(signal)


	def queue_signal(self, plugin: str, signal: dict) -> None:
		self.signal_queue.put_nowait({'plugin': plugin, 'signal': signal})


	def schedule_signal(self, seconds: int, plugin: str, signal: dict, id=None, mode='single') -> None:
		match mode:
			case 'single':
				self.scheduler.add_job(self.on_scheduler, 'date', run_date=datetime_datetime.now()+datetime_timedelta(seconds=seconds),
				                       args=[plugin, signal], id=id, name=id, replace_existing=True)
			case 'interval':
				self.scheduler.add_job(self.on_scheduler, 'interval', seconds=seconds,
				                       args=[plugin, signal], id=id, name=id, replace_existing=True)
			case other:
				logging_getLogger().error(f"unsupported schedule mode '{mode}' in Daemon.schedule_signal()")


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

