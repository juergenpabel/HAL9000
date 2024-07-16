#!/usr/bin/env python3

from os.path import exists as os_path_exists
from sys import argv as sys_argv, exit as sys_exit
from time import monotonic as time_monotonic
from json import loads as json_loads, dumps as json_dumps
from logging import getLogger as logging_getLogger
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
		self.frontends = []
		self.tasks = {}


	async def configure(self, filename):
		logging_getLogger("uvicorn").info(f"[frontend] Using configuration file '{filename}'")
		self.configuration = configparser_ConfigParser(delimiters='=', interpolation=None,
		                                          converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
		                                                      'string': lambda string: string.strip('"').strip("'")})
		self.configuration.read(filename)
		logging_getLogger("uvicorn").info(f"[frontend] Switching to configured log-level '{self.configuration.get('frontend', 'log-level', fallback='INFO')}'...")
		logging_getLogger('uvicorn').setLevel(self.configuration.get('frontend', 'log-level', fallback='INFO'))
		logging_getLogger("uvicorn").info(f"[frontend] connecting to MQTT broker...")
		self.mqtt_client = mqtt_Client(mqtt_CallbackAPIVersion.VERSION2, client_id='frontend')
		for counter in range(self.configuration.get('frontend', 'mqtt-connection-attempts', fallback=10)):
			if self.mqtt_client.is_connected() is False:
				logging_getLogger("uvicorn").debug(f"[frontend] - MQTT connection attempt #{counter+1}")
				try:
					self.mqtt_client.connect(self.configuration.getstring('frontend', 'broker-ip', fallback='127.0.0.1'),
					                         self.configuration.getstring('frontend', 'broker-port', fallback=1883))
					self.mqtt_client.subscribe('hal9000/command/frontend/#')
					self.mqtt_client.on_message = self.on_mqtt_message
					self.mqtt_client.loop(timeout=1)
				except ConnectionRefusedError:
					await asyncio_sleep(1)
					self.mqtt_client = mqtt_Client(mqtt_CallbackAPIVersion.VERSION2, client_id='frontend')
		if self.mqtt_client.is_connected() is False:
			logging_getLogger("uvicorn").error(f"[frontend] ERROR: MQTT broker unavailable at '{self.configuration.getstring('frontend', 'broker-ip', fallback='127.0.0.1')}'")
			return False
		logging_getLogger("uvicorn").info(f"[frontend] ...connected to '{self.configuration.getstring('frontend', 'broker-ip', fallback='127.0.0.1')}'")
		return True


	def add_frontend(self, frontend):
		self.frontends.append(frontend)


	def on_mqtt_message(self, client, userdata, message):
		topic = message.topic[25:] # remove 'hal9000/command/frontend/' prefix
		payload = message.payload.decode('utf-8')
		match topic:
			case 'runlevel':
				if self.startup is False:
					frontends_runlevel = []
					for frontend in self.frontends:
						frontends_runlevel.append(frontend.runlevel)
					if Frontend.FRONTEND_RUNLEVEL_RUNNING in frontends_runlevel:
						self.mqtt_client.publish('hal9000/event/frontend/runlevel', Frontend.FRONTEND_RUNLEVEL_RUNNING)
					elif Frontend.FRONTEND_RUNLEVEL_READY in frontends_runlevel:
						self.mqtt_client.publish('hal9000/event/frontend/runlevel', Frontend.FRONTEND_RUNLEVEL_READY)
					else:
						self.mqtt_client.publish('hal9000/event/frontend/runlevel', Frontend.FRONTEND_RUNLEVEL_STARTING)
				else:
					logging_getLogger("uvicorn").debug(f"[frontend] ignoring runlevel command because startup is still in progress")
			case 'status':
				if self.startup is False:
					frontends_status = []
					for frontend in self.frontends:
						frontends_status.append(frontend.status)
					if Frontend.FRONTEND_STATUS_ONLINE in frontends_status:
						self.mqtt_client.publish('hal9000/event/frontend/status', Frontend.FRONTEND_STATUS_ONLINE)
					else:
						self.mqtt_client.publish('hal9000/event/frontend/status', Frontend.FRONTEND_STATUS_OFFLINE)
				else:
					logging_getLogger("uvicorn").debug(f"[frontend] ignoring status command because startup is still in progress")
			case other:
				try:
					payload = json_loads(payload)
				except Exception:
					pass
				for frontend in self.frontends:
					frontend.commands.put_nowait({"topic": topic, "payload": payload})


	async def command_listener(self):
		startup_last_publish = time_monotonic()
		while self.tasks['command_listener'].cancelled() is False:
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
				self.mqtt_client.connect(self.configuration.getstring('frontend', 'broker-ip', fallback='127.0.0.1'),
				                         self.configuration.getstring('frontend', 'broker-port', fallback=1883))
				self.mqtt_client.subscribe('hal9000/command/frontend/#')
				self.mqtt_client.on_message = self.on_mqtt_message
				self.mqtt_client.loop(timeout=1)
			except ConnectionRefusedError:
				await asyncio_sleep(1)
		logging_getLogger("uvicorn").info(f"[frontend] command_listener() exiting due to task being cancelled")


	async def event_listener(self):
		while self.tasks['event_listener'].cancelled() is False:
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
									topic = f'hal9000/event/frontend/{topic}'
								if isinstance(payload, str) is False:
									try:
										payload = json_dumps(payload)
									except:
										pass
								self.mqtt_client.publish(topic, payload)
					await asyncio_sleep(0.01)
				case False:
					logging_getLogger("uvicorn").debug(f"[frontend] event_listener() no mqtt connection...")
					await asyncio_sleep(1)
		logging_getLogger("uvicorn").info(f"[frontend] event_listener() exiting due to task being cancelled")


async def fastapi_lifespan(app: fastapi_FastAPI):
	if len(sys_argv) != 2:
		sys_exit(1)
	manager = FrontendManager()
	if await manager.configure(sys_argv[1]) is False:
		logging_getLogger("uvicorn").critical(f"[frontend] configuration failed, exiting...")
		sys_exit(1)
	manager.tasks['command_listener'] = asyncio_create_task(manager.command_listener())
	manager.tasks['event_listener'] = asyncio_create_task(manager.event_listener())
	logging_getLogger("uvicorn").info(f"[frontend] Starting frontend 'flet'...'")
	frontend_flet = hal9000.frontend.flet.HAL9000(app)
	match await frontend_flet.configure(manager.configuration):
		case True:
			manager.add_frontend(frontend_flet)
			await frontend_flet.start()
			logging_getLogger("uvicorn").info(f"[frontend] ...frontend 'flet' started")
		case False:
			logging_getLogger("uvicorn").error(f"[frontend] configuration of frontend 'flet' failed, check the configuration ('{manager.configuration}')' for potential issues")
		case None:
			logging_getLogger("uvicorn").info(f"[frontend] ...ignoring frontend 'flet' (BUG?)")
	logging_getLogger("uvicorn").info(f"[frontend] Starting frontend 'arduino'...")
	frontend_arduino = hal9000.frontend.arduino.HAL9000(app)
	match await frontend_arduino.configure(manager.configuration):
		case True:
			manager.add_frontend(frontend_arduino)
			await frontend_arduino.start()
			logging_getLogger("uvicorn").info(f"[frontend] ...frontend 'arduino' started")
		case False:
			logging_getLogger("uvicorn").error(f"[frontend] configuration of frontend 'arduino' failed, check the configuration ('{manager.configuration}')' for potential issues")
		case None:
			logging_getLogger("uvicorn").info(f"[frontend] ...ignoring frontend 'arduino' (device not present)")
	yield


app = fastapi_FastAPI(lifespan=fastapi_lifespan)
if __name__ == '__main__':
	if os_path_exists('assets') is False:
		logging_getLogger().critical("[frontend] missing 'assets' directory (or symlink to directory)")
		sys_exit(1)
	try:
		uvicorn_run('frontend:app', host='0.0.0.0', port=9000, log_level='info')
	except KeyboardInterrupt:
		logging_getLogger().info("[frontend] exiting due to CTRL-C")
	finally:
		logging_getLogger().info("[frontend] terminating")

