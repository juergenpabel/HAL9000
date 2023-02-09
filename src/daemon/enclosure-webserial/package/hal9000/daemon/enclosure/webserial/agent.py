#!/usr/bin/env python3

import logging
import json
from configparser import ConfigParser

import asyncio
import asyncio_mqtt


class Agent:

	def __init__(self):
		self.logger = logging.getLogger()
		self.config = dict()


	def configure(self, configuration: ConfigParser) -> None:
		self.config['agent:trace']   = configuration.getboolean('agent', 'trace', fallback=False)
		self.config['agent:address'] = configuration.getstring('agent', 'device', fallback='127.0.0.1')
		self.config['agent:event-topic-base']   = configuration.getstring('agent', 'event-topic-base',   fallback='hal9000/daemon/enclosure-service/event')
		self.config['agent:command-topic-base'] = configuration.getstring('agent', 'command-topic-base', fallback='hal9000/daemon/enclosure-service/command')


	async def send(self, topic: str, payload, quote_payload: bool = False) -> None:
		topic = f"{self.config['agent:event-topic-base']}/{topic}"
		if type(payload) == str and quote_payload is True:
			payload = payload.replace('"', '\\"')
			payload = f"\"{payload}\""
		if type(payload) == dict:
			payload = json.dumps(payload)
		if self.config['agent:trace'] is True:
			self.logger.debug(f"MQTT.send: {topic} => {payload}")
		await self.mqtt.publish(topic, payload=payload)


	async def loop(self, target_writer):
		try:
			self.logger.info(f"agent => Connecting to '{self.config['agent:address']}'...")
			async with asyncio_mqtt.Client(self.config['agent:address']) as self.mqtt:
				async with self.mqtt.messages() as messages:
					await self.mqtt.subscribe(f"{self.config['agent:command-topic-base']}/+")
					async for message in messages:
						base, topic = str(message.topic).rsplit('/', 1)
						payload = message.payload.decode('utf-8')
						if base == self.config['agent:command-topic-base']:
							await target_writer.send(topic, payload)
		except BaseException as e:
			self.logger.error(f"{str(e)}({type(e)})")

