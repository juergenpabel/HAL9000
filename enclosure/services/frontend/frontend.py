#!/usr/bin/env python3

import os
import sys
import json
import logging

import asyncio
import fastapi
import uvicorn
import paho.mqtt.client as mqtt

from hal9000.frontend import Frontend
import hal9000.frontend.arduino
import hal9000.frontend.flet

class FrontendManager:

	def __init__(self):
		self.frontends = []
		self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='frontend')
		self.mqtt_client.connect(os.getenv('MQTT_SERVER', default='127.0.0.1'), int(os.getenv('MQTT_PORT', default='1883')))
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
			payload = json.loads(payload)
		except Exception:
			pass
		for frontend in self.frontends:
			frontend.commands.put_nowait({"topic": message.topic[25:], "payload": payload})


	async def command_listener(self):
		while self.mqtt_client.is_connected() is True:
			status = self.mqtt_client.loop(timeout=0.01)
			await asyncio.sleep(0.01)
		raise Exception("ERROR: MQTT disconnected from '{os.getenv('MQTT_SERVER', default='127.0.0.1')}' for command_listener")


	async def event_listener(self):
		while self.mqtt_client.is_connected() is True:
			for frontend in self.frontends:
				if frontend.events.empty() is False:
					event = await frontend.events.get()
					topic = event['topic']
					payload = event['payload']
					if isinstance(payload, str) is False:
						try:
							payload = json.dumps(payload)
						except:
							pass
					self.mqtt_client.publish(f'hal9000/event/frontend/{topic}', payload)
			await asyncio.sleep(0.01)
		raise Exception("ERROR: MQTT disconnected from '{os.getenv('MQTT_SERVER', default='127.0.0.1')}' for event_listener")


async def fastapi_lifespan(app: fastapi.FastAPI):
	configuration = None
	if len(sys.argv) > 1:
		configuration = sys.argv[1]
	print(configuration, flush=True)
	manager = FrontendManager()
	frontend_arduino = hal9000.frontend.arduino.HAL9000(app)
	if await frontend_arduino.configure(configuration) is True:
		manager.add_frontend(frontend_arduino)
	frontend_flet = hal9000.frontend.flet.HAL9000(app)
	if await frontend_flet.configure(configuration) is True:
		manager.add_frontend(frontend_flet)
	asyncio.create_task(manager.command_listener())
	asyncio.create_task(manager.event_listener())
	yield


app = fastapi.FastAPI(lifespan=fastapi_lifespan)
if __name__ == '__main__':
	uvicorn.run('frontend:app', host='0.0.0.0', port=9000, log_level='info')

