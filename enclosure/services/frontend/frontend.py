#!/usr/bin/env python3

from os.path import exists as os_path_exists
from sys import argv as sys_argv, exit as sys_exit
from time import monotonic as time_monotonic
from json import loads as json_loads, dumps as json_dumps
from logging import getLogger as logging_getLogger, \
                    addLevelName as logging_addLevelName
from importlib import import_module as importlib_import_module
from configparser import ConfigParser as configparser_ConfigParser
from paho.mqtt.client import Client as mqtt_Client, CallbackAPIVersion as mqtt_CallbackAPIVersion
from asyncio import sleep as asyncio_sleep, create_task as asyncio_create_task
from fastapi import FastAPI as fastapi_FastAPI
from uvicorn import run as uvicorn_run
from uvicorn.config import LOGGING_CONFIG as uvicorn_config_LOGGING_CONFIG

from hal9000.frontend import Frontend, RUNLEVEL, STATUS
import hal9000.frontend.arduino
import hal9000.frontend.flet

class FrontendManager:

	def __init__(self):
		self.configuration = None
		self.configuration_filename = None
		self.config = {}
		self.frontends = []
		self.tasks = {}
		self.mqtt_client = None


	async def configure(self, filename):
		logging_getLogger("uvicorn").info(f"[frontend] Using configuration file '{filename}'")
		self.configuration_filename = filename
		self.configuration = configparser_ConfigParser(delimiters='=', interpolation=None,
		                                          converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
		                                                      'string': lambda string: string.strip('"').strip("'")})
		self.configuration.read(filename)
		self.config['frontend:log-level'] = self.configuration.get('frontend', 'log-level', fallback='INFO')
		self.config['frontend:broker-ipv4'] = self.configuration.getstring('frontend', 'mqtt-broker-ipv4', fallback='127.0.0.1')
		self.config['frontend:broker-port'] = self.configuration.getint('frontend', 'mqtt-broker-port', fallback=1883)
		self.config['frontend:broker-clientid'] = self.configuration.getstring('frontend', 'mqtt-broker-clientid', fallback='frontend')
		self.config['frontend:broker-keepalive'] = self.configuration.getint('frontend', 'mqtt-broker-keepalive', fallback=0)
		self.config['frontend:plugins'] = self.configuration.getlist('frontend', 'plugins', fallback=[])
		for name in self.config['frontend:plugins']:
			self.config[f'frontend:{name}:module'] = self.configuration.get(f'frontend:{name}', 'module', fallback=None)
		logging_getLogger("uvicorn").info(f"[frontend] Switching to configured log-level '{self.config['frontend:log-level']}'...")
		logging_getLogger('uvicorn').setLevel(self.config['frontend:log-level'])
		logging_getLogger("uvicorn").info(f"[frontend] connecting to MQTT broker ({self.config['frontend:broker-ipv4']})...")
		for counter in range(0, 4):
			if self.mqtt_client is None or self.mqtt_client.is_connected() is False:
				logging_getLogger("uvicorn").debug(f"[frontend] - MQTT connection attempt #{counter+1} (of 5)")
				if await self.mqtt_connect() is False:
					delay = pow(2, counter)
					logging_getLogger("uvicorn").debug(f"[frontend] - MQTT connection attempt failed, waiting {delay} seconds before next attempt")
					await asyncio_sleep(delay)
		if self.mqtt_client.is_connected() is False:
			logging_getLogger("uvicorn").error(f"[frontend] ERROR: MQTT broker unavailable at '{self.config['frontend:broker-ipv4']}'")
			return False
		logging_getLogger("uvicorn").info(f"[frontend] ...connected to MQTT broker ({self.config['frontend:broker-ipv4']})")
		return True


	def add_frontend(self, frontend):
		self.frontends.append(frontend)


	def calculate_runlevel(self) -> str:
		frontends_runlevel = []
		for frontend in self.frontends:
			frontends_runlevel.append(frontend.runlevel)
		if RUNLEVEL.RUNNING in frontends_runlevel:
			return RUNLEVEL.RUNNING
		elif RUNLEVEL.SYNCING in frontends_runlevel:
			return RUNLEVEL.SYNCING
		return RUNLEVEL.STARTING


	def calculate_status(self) -> str:
		frontends_status = []
		for frontend in self.frontends:
			frontends_status.append(frontend.status)
		if STATUS.ONLINE in frontends_status:
			return STATUS.ONLINE
		return STATUS.OFFLINE


	async def mqtt_connect(self) -> bool:
		if self.mqtt_client is not None and self.mqtt_client.is_connected() is True:
			return True
		try:
			self.mqtt_client = mqtt_Client(mqtt_CallbackAPIVersion.VERSION2, client_id=self.config['frontend:broker-clientid'])
			self.mqtt_client.will_set('hal9000/event/frontend/runlevel', 'killed')
			self.mqtt_client.connect(self.config['frontend:broker-ipv4'], self.config['frontend:broker-port'],
			                         keepalive=self.config['frontend:broker-keepalive'])
			self.mqtt_client.subscribe('hal9000/command/frontend/#')
			self.mqtt_client.subscribe('hal9000/event/brain/runlevel')
			self.mqtt_client.on_message = self.on_mqtt_message
			self.mqtt_client.loop(timeout=1)
		except ConnectionRefusedError:
			self.mqtt_client = None
			return False
		return self.mqtt_client.is_connected()


	async def mqtt_manager(self):
		while self.tasks['mqtt_manager'].cancelled() is False:
			if self.mqtt_client is None or self.mqtt_client.is_connected() is False:
				if await self.mqtt_connect() is False:
					logging_getLogger("uvicorn").warning(f"[frontend] - MQTT re-connection attempt failed, waiting 1 second before next attempt")
					await asyncio_sleep(1)
			if self.mqtt_client is not None and self.mqtt_client.is_connected() is True:
				self.mqtt_client.loop(timeout=0.01)
				await asyncio_sleep(0.01)
		logging_getLogger("uvicorn").info(f"[frontend] mqtt_manager() exiting due to task being cancelled")


	def on_mqtt_message(self, client, userdata, message):
		topic = message.topic
		payload = message.payload.decode('utf-8', 'surrogateescape')
		logging_getLogger('uvicorn').log(Frontend.LOG_LEVEL_TRACE, f"[frontend] received MQTT message: {topic} => {payload}")
		if topic == 'hal9000/event/brain/runlevel':
			match payload:
				case 'killed':
					logging_getLogger("uvicorn").info(f"[frontend] received mqtt message that service 'brain' has died, showing error screen")
					for frontend in self.frontends:
						frontend.commands.put_nowait({'topic': 'gui/screen', 'payload': {'error': {'id': '100', 'title': "System offline"}}})
				case 'running':
					logging_getLogger("uvicorn").info(f"[frontend] received mqtt message that service 'brain' is running again")
			return
		match topic[25:]: #remove 'hal9000/command/frontend/' prefix
			case 'runlevel':
				if payload is None or payload == '':
					self.frontends[0].events.put_nowait({'topic': 'hal9000/event/frontend/runlevel', 'payload': self.calculate_runlevel()})
				else:
					logging_getLogger("uvicorn").warn(f"[frontend] ignoring mqtt command 'runlevel' with payload '{payload}' because 'runlevel' is read-only")
			case 'status':
				if payload is None or payload == '':
					if self.calculate_runlevel() == RUNLEVEL.RUNNING:
						self.frontends[0].events.put_nowait({'topic': 'hal9000/event/frontend/status', 'payload': self.calculate_status()})
				else:
					logging_getLogger("uvicorn").warn(f"[frontend] ignoring mqtt command 'status' with payload '{payload}' because 'status' is read-only")
			case other:
				try:
					payload = json_loads(payload)
					if isinstance(payload, dict) is True:
						if 'trace' in payload:
							del payload['trace']
				except Exception:
					pass
				for frontend in self.frontends:
					frontend.commands.put_nowait({"topic": topic[25:], "payload": payload})


	async def mqtt_publisher(self):
		while self.mqtt_client is None or self.mqtt_client.is_connected() is False:
			if self.tasks['mqtt_publisher'].cancelled() is True:
				return
			await asyncio_sleep(0.1)
		self.mqtt_client.publish('hal9000/event/frontend/runlevel', RUNLEVEL.STARTING)
		current_runlevel = RUNLEVEL.STARTING
		current_status = 'unknown'
		while self.tasks['mqtt_publisher'].cancelled() is False:
			if self.mqtt_client is not None and self.mqtt_client.is_connected() is True:
				for frontend in self.frontends:
					if frontend.events.empty() is False:
						event = await frontend.events.get()
						if 'topic' in event and 'payload' in event:
							topic = event['topic']
							payload = event['payload']
							if topic.count('/') in [0, 1]:
								match topic:
									case 'runlevel':
										calculated_runlevel = self.calculate_runlevel()
										if calculated_runlevel != current_runlevel:
											logging_getLogger("uvicorn").info(f"[frontend] runlevel is now '{calculated_runlevel}'")
											if calculated_runlevel == RUNLEVEL.RUNNING: #publish intermediate 'syncing' runlevel
												self.mqtt_client.publish('hal9000/event/frontend/runlevel', RUNLEVEL.SYNCING)
											topic = 'hal9000/event/frontend/runlevel'
											payload = calculated_runlevel
											current_runlevel = calculated_runlevel
										else:
											topic = None
									case 'status':
										status = self.calculate_status()
										if status != current_status:
											current_status = status
											logging_getLogger("uvicorn").info(f"[frontend] status is now '{status}'")
											topic = 'hal9000/event/frontend/status'
											payload = status
										else:
											topic = None
									case other:
										topic = f'hal9000/event/frontend/{topic}'
							if topic is not None:
								if isinstance(payload, str) is False:
									try:
										payload = json_dumps(payload)
									except:
										pass
								self.mqtt_client.publish(topic, payload)
								logging_getLogger('uvicorn').log(Frontend.LOG_LEVEL_TRACE, f"[frontend] published MQTT message: " \
								                                                           f"{topic} => {payload}")
			await asyncio_sleep(0.01)
		logging_getLogger("uvicorn").info(f"[frontend] mqtt_publisher() exiting due to task being cancelled")


async def fastapi_lifespan(app: fastapi_FastAPI):
	if len(sys_argv) != 2:
		sys_exit(1)
	manager = FrontendManager()
	if await manager.configure(sys_argv[1]) is False:
		logging_getLogger("uvicorn").critical(f"[frontend] configuration failed, exiting...")
		sys_exit(1)
	manager.tasks['mqtt_manager'] = asyncio_create_task(manager.mqtt_manager())
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
						logging_getLogger("uvicorn").critical(f"[frontend] configuration of frontend '{frontend_name}' failed")
					case None:
						logging_getLogger("uvicorn").info(f"[frontend] ...not starting frontend '{frontend_name}' as per configuration result")
	yield


app = fastapi_FastAPI(lifespan=fastapi_lifespan)
if __name__ == '__main__':
	logging_addLevelName(Frontend.LOG_LEVEL_TRACE, 'TRACE')
	if os_path_exists('resources') is False:
		logging_getLogger().critical("[frontend] missing 'resources' directory (or symlink to directory)")
		sys_exit(1)
	logging_getLogger().info("[frontend] starting...")
	try:
		uvicorn_config_LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s %(levelprefix)s %(message)s"
		uvicorn_run('frontend:app', host='0.0.0.0', port=9000, log_level='info')
	except KeyboardInterrupt:
		logging_getLogger().info("[frontend] exiting due to CTRL-C")
	finally:
		logging_getLogger().info("[frontend] terminating")

