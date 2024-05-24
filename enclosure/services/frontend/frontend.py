#!/usr/bin/env python3

from os import getenv as os_getenv
from sys import argv as sys_argv
from time import monotonic as time_monotonic
from json import loads as json_loads, dumps as json_dumps

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
		self.mqtt_client = mqtt_Client(mqtt_CallbackAPIVersion.VERSION2, client_id='frontend')
		self.mqtt_client.connect(os_getenv('MQTT_SERVER', default='127.0.0.1'), int(os_getenv('MQTT_PORT', default='1883')))
		self.mqtt_client.subscribe('hal9000/command/frontend/#')
		self.mqtt_client.on_message = self.on_mqtt_message
		self.mqtt_client.loop(timeout=1)
		if self.mqtt_client.is_connected() is False:
			raise Exception("no mqtt")


	def add_frontend(self, frontend):
		self.frontends.append(frontend)


	def on_mqtt_message(self, client, userdata, message):
		payload = message.payload.decode('utf-8')
		try:
			payload = json_loads(payload)
		except Exception:
			pass
		if self.startup is True:
			self.startup = False
		for frontend in self.frontends:
			frontend.commands.put_nowait({"topic": message.topic[25:], "payload": payload})


	async def command_listener(self):
		startup_last_publish = time_monotonic()
		while self.mqtt_client.is_connected() is True:
			if self.startup is True:
				if (time_monotonic() - startup_last_publish) > 1:
					startup_last_publish = time_monotonic()
					self.mqtt_client.publish('hal9000/event/frontend/interface/state', 'online')
			status = self.mqtt_client.loop(timeout=0.01)
			await asyncio_sleep(0.01)
		raise Exception("ERROR: MQTT disconnected from '{os_getenv('MQTT_SERVER', default='127.0.0.1')}' for command_listener")


	async def event_listener(self):
		while self.mqtt_client.is_connected() is True:
			for frontend in self.frontends:
				if frontend.events.empty() is False:
					event = await frontend.events.get()
					topic = event['topic']
					payload = event['payload']
					if isinstance(payload, str) is False:
						try:
							payload = json_dumps(payload)
						except:
							pass
					self.mqtt_client.publish(f'hal9000/event/frontend/{topic}', payload)
			await asyncio_sleep(0.01)
		raise Exception("ERROR: MQTT disconnected from '{os_getenv('MQTT_SERVER', default='127.0.0.1')}' for event_listener")


async def fastapi_lifespan(app: fastapi_FastAPI):
	configuration = None
	if len(sys_argv) > 1:
		configuration = sys_argv[1]
	print(configuration, flush=True)
	manager = FrontendManager()
	frontend_arduino = hal9000.frontend.arduino.HAL9000(app)
	if await frontend_arduino.configure(configuration) is True:
		manager.add_frontend(frontend_arduino)
	frontend_flet = hal9000.frontend.flet.HAL9000(app)
	if await frontend_flet.configure(configuration) is True:
		manager.add_frontend(frontend_flet)
	asyncio_create_task(manager.command_listener())
	asyncio_create_task(manager.event_listener())
	yield


app = fastapi_FastAPI(lifespan=fastapi_lifespan)
if __name__ == '__main__':
	uvicorn_run('frontend:app', host='0.0.0.0', port=9000, log_level='info')

