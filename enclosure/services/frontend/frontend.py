#!/usr/bin/env python3

from os.path import exists as os_path_exists
from sys import argv as sys_argv, exit as sys_exit
from time import monotonic as time_monotonic
from json import loads as json_loads, dumps as json_dumps
from logging import getLogger as logging_getLogger, \
                    addLevelName as logging_addLevelName
from importlib import import_module as importlib_import_module
from configparser import ConfigParser as configparser_ConfigParser
from asyncio import sleep as asyncio_sleep, create_task as asyncio_create_task
from fastapi import FastAPI as fastapi_FastAPI
from uvicorn import run as uvicorn_run
from paho.mqtt.client import Client as mqtt_Client, CallbackAPIVersion as mqtt_CallbackAPIVersion

from hal9000.frontend import Frontend
import hal9000.frontend.arduino
import hal9000.frontend.flet

class FrontendManager:

	def __init__(self):
		self.startup = True
		self.config = {}
		self.frontends = []
		self.tasks = {}


	async def configure(self, filename):
		logging_getLogger("uvicorn").info(f"[frontend] Using configuration file '{filename}'")
		self.configuration = configparser_ConfigParser(delimiters='=', interpolation=None,
		                                          converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
		                                                      'string': lambda string: string.strip('"').strip("'")})
		self.configuration.read(filename)
		self.config['frontend:log-level'] = self.configuration.get('frontend', 'log-level', fallback='INFO')
		self.config['frontend:broker-ipv4'] = self.configuration.getstring('frontend', 'mqtt-broker-ipv4', fallback='127.0.0.1')
		self.config['frontend:broker-port'] = self.configuration.getint('frontend', 'mqtt-broker-port', fallback=1883)
		self.config['frontend:plugins'] = self.configuration.getlist('frontend', 'plugins', fallback=[])
		for name in self.config['frontend:plugins']:
			self.config[f'frontend:{name}:module'] = self.configuration.get(f'frontend:{name}', 'module', fallback=None)
		logging_getLogger("uvicorn").info(f"[frontend] Switching to configured log-level '{self.config['frontend:log-level']}'...")
		logging_getLogger('uvicorn').setLevel(self.config['frontend:log-level'])
		logging_getLogger("uvicorn").info(f"[frontend] connecting to MQTT broker...")
		self.mqtt_client = mqtt_Client(mqtt_CallbackAPIVersion.VERSION2, client_id='frontend')
		for counter in range(0, 4):
			if self.mqtt_client.is_connected() is False:
				logging_getLogger("uvicorn").debug(f"[frontend] - MQTT connection attempt #{counter+1}")
				if await self.mqtt_connect() is False:
					delay = pow(2, counter)
					logging_getLogger("uvicorn").debug(f"[frontend] - MQTT connection attempt failed, waiting {delay} seconds before next attempt")
					await asyncio_sleep(delay)
		if self.mqtt_client.is_connected() is False:
			logging_getLogger("uvicorn").error(f"[frontend] ERROR: MQTT broker unavailable at '{self.config['frontend:broker-ipv4']}'")
			return False
		logging_getLogger("uvicorn").info(f"[frontend] ...connected to '{self.config['frontend:broker-ipv4']}'")
		return True


	def add_frontend(self, frontend):
		self.frontends.append(frontend)


	def calculate_runlevel(self) -> str:
		frontends_runlevel = []
		for frontend in self.frontends:
			frontends_runlevel.append(frontend.runlevel)
		if Frontend.FRONTEND_RUNLEVEL_RUNNING in frontends_runlevel:
			return Frontend.FRONTEND_RUNLEVEL_RUNNING
		elif Frontend.FRONTEND_RUNLEVEL_READY in frontends_runlevel:
			return Frontend.FRONTEND_RUNLEVEL_READY
		return Frontend.FRONTEND_RUNLEVEL_STARTING


	def calculate_status(self) -> str:
		frontends_status = []
		for frontend in self.frontends:
			frontends_status.append(frontend.status)
		if Frontend.FRONTEND_STATUS_ONLINE in frontends_status:
			return Frontend.FRONTEND_STATUS_ONLINE
		return Frontend.FRONTEND_STATUS_OFFLINE


	async def mqtt_connect(self) -> bool:
		if self.mqtt_client.is_connected() is False:
			try:
				self.mqtt_client.will_set('hal9000/event/frontend/runlevel', 'killed')
				self.mqtt_client.connect(self.config['frontend:broker-ipv4'], self.config['frontend:broker-port'])
				self.mqtt_client.subscribe('hal9000/command/frontend/#')
				self.mqtt_client.subscribe('hal9000/event/brain/runlevel')
				self.mqtt_client.on_message = self.mqtt_subscriber_message
				self.mqtt_client.loop(timeout=1)
			except ConnectionRefusedError:
				self.mqtt_client = mqtt_Client(mqtt_CallbackAPIVersion.VERSION2, client_id='frontend')
		return self.mqtt_client.is_connected()


	def mqtt_subscriber_message(self, client, userdata, message):
		topic = message.topic
		payload = message.payload.decode('utf-8', 'surrogateescape')
		if topic == 'hal9000/event/brain/runlevel':
			if payload == 'killed':
				logging_getLogger("uvicorn").warning(f"[frontend] received mqtt message that brain component has disconnected, showing error screen")
				for frontend in self.frontends:
					frontend.commands.put_nowait({"topic": 'gui/screen', "payload": {'on': {}}})
					frontend.commands.put_nowait({"topic": 'gui/screen', "payload": {'error': {'message': 'System failure',
					                                                                           'url': 'https://github.com/juergenpabel/HAL9000/wiki/ERROR_07',
					                                                                           'id': '07'}}})
			return
		match topic[25:]: #remove 'hal9000/command/frontend/' prefix
			case 'runlevel':
				if self.startup is False:
					self.mqtt_client.publish('hal9000/event/frontend/runlevel', self.calculate_runlevel())
				else:
					logging_getLogger("uvicorn").debug(f"[frontend] ignoring mqtt command 'runlevel' because startup is still in progress")
			case 'status':
				if self.startup is False:
					self.mqtt_client.publish('hal9000/event/frontend/status', self.calculate_status())
				else:
					logging_getLogger("uvicorn").debug(f"[frontend] ignoring mqtt command 'status' because startup is still in progress")
			case other:
				try:
					payload = json_loads(payload)
				except Exception:
					pass
				for frontend in self.frontends:
					frontend.commands.put_nowait({"topic": topic[25:], "payload": payload})


	async def mqtt_subscriber(self):
		startup_last_publish = time_monotonic()
		while self.tasks['mqtt_subscriber'].cancelled() is False:
			while self.mqtt_client.is_connected():
				if self.startup is True:
					if (time_monotonic() - startup_last_publish) > 1:
						startup_last_publish = time_monotonic()
						self.mqtt_client.publish('hal9000/event/frontend/runlevel', 'starting')
				self.mqtt_client.loop(timeout=0.01)
				await asyncio_sleep(0.01)
			logging_getLogger("uvicorn").warning(f"[frontend] MQTT is disconnected, reconnecting...")
			try:
				self.mqtt_client = mqtt_Client(mqtt_CallbackAPIVersion.VERSION2, client_id='frontend')
				self.mqtt_client.connect(self.config['frontend:broker-ipv4'], self.config['frontend:broker-port'])
				self.mqtt_client.subscribe('hal9000/command/frontend/#')
				self.mqtt_client.on_message = self.mqtt_subscriber_message
				self.mqtt_client.loop(timeout=1)
			except ConnectionRefusedError:
				await asyncio_sleep(1)
		logging_getLogger("uvicorn").info(f"[frontend] mqtt_subscriber() exiting due to task being cancelled")


	async def mqtt_publisher(self):
		last_runlevel = None
		last_status = None
		while self.tasks['mqtt_publisher'].cancelled() is False:
			match self.mqtt_client.is_connected():
				case True:
					for frontend in self.frontends:
						if frontend.events.empty() is False:
							if self.startup is True:
								logging_getLogger("uvicorn").info(f"[frontend] startup completed")
								self.mqtt_client.publish('hal9000/event/frontend/runlevel', Frontend.FRONTEND_RUNLEVEL_READY)
								self.startup = False
							event = await frontend.events.get()
							if 'topic' in event and 'payload' in event:
								topic = event['topic']
								payload = event['payload']
								if topic.count('/') in [0, 1]:
									if topic == 'runlevel':
										runlevel = self.calculate_runlevel()
										if runlevel != last_runlevel:
											last_runlevel = runlevel
											logging_getLogger("uvicorn").info(f"[frontend] runlevel is now '{runlevel}'")
										payload = runlevel
									if topic == 'status':
										status = self.calculate_status()
										if status != last_status:
											last_status = status
											logging_getLogger("uvicorn").info(f"[frontend] status is now '{status}'")
										payload = status
									topic = f'hal9000/event/frontend/{topic}'
								if isinstance(payload, str) is False:
									try:
										payload = json_dumps(payload)
									except:
										pass
								self.mqtt_client.publish(topic, payload)
					await asyncio_sleep(0.01)
				case False:
					logging_getLogger("uvicorn").debug(f"[frontend] mqtt_publisher() no mqtt connection...")
					await asyncio_sleep(1)
		logging_getLogger("uvicorn").info(f"[frontend] mqtt_publisher() exiting due to task being cancelled")


async def fastapi_lifespan(app: fastapi_FastAPI):
	if len(sys_argv) != 2:
		sys_exit(1)
	manager = FrontendManager()
	if await manager.configure(sys_argv[1]) is False:
		logging_getLogger("uvicorn").critical(f"[frontend] configuration failed, exiting...")
		sys_exit(1)
	manager.tasks['mqtt_subscriber'] = asyncio_create_task(manager.mqtt_subscriber())
	manager.tasks['mqtt_publisher'] = asyncio_create_task(manager.mqtt_publisher())
	for frontend_name in manager.config['frontend:plugins']:
		logging_getLogger("uvicorn").info(f"[frontend] Loading frontend '{frontend_name}'...'")
		module = importlib_import_module(manager.config[f'frontend:{frontend_name}:module'])
		if module is not None:
			frontend_class = getattr(module, 'HAL9000', None)
			if frontend_class is not None:
				logging_getLogger("uvicorn").info(f"[frontend] Starting frontend '{frontend_name}'...'")
				frontend_instance = frontend_class(app)
				match await frontend_instance.configure(manager.configuration):
					case True:
						manager.add_frontend(frontend_instance)
						await frontend_instance.start()
						logging_getLogger("uvicorn").info(f"[frontend] ...frontend '{frontend_name}' started")
					case False:
						logging_getLogger("uvicorn").error(f"[frontend] configuration of frontend '{frontend_name}' failed, check the " \
						                                   f"configuration ('{manager.configuration}')' for potential issues")
					case None:
						logging_getLogger("uvicorn").info(f"[frontend] ...not starting frontend '{frontend_name}' as per configuration result")
	yield


app = fastapi_FastAPI(lifespan=fastapi_lifespan)
if __name__ == '__main__':
	logging_addLevelName(Frontend.LOG_LEVEL_TRACE, 'TRACE')
	if os_path_exists('assets') is False:
		logging_getLogger().critical("[frontend] missing 'assets' directory (or symlink to directory)")
		sys_exit(1)
	try:
		uvicorn_run('frontend:app', host='0.0.0.0', port=9000, log_level='info')
	except KeyboardInterrupt:
		logging_getLogger().info("[frontend] exiting due to CTRL-C")
	finally:
		logging_getLogger().info("[frontend] terminating")

