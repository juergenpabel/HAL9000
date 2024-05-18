#!/usr/bin/env python3

import os
import time
import json
import serial
import fastapi

import asyncio

from hal9000.frontend import Frontend

class HAL9000(Frontend):

	def __init__(self, app: fastapi.FastAPI):
		super().__init__()
		self.serial = None

	async def configure(self, filename) -> bool:
		if await super().configure(filename) is False:
			print(f"[frontend:arduino] parsing '{filename}' failed")
			return False
		arduino_device   = self.config.getstring('arduino', 'device',   fallback='/dev/ttyHAL9000')
		arduino_baudrate = self.config.getint   ('arduino', 'baudrate', fallback=115200)
		arduino_timeout  = self.config.getfloat ('arduino', 'timeout',  fallback=0.01)
		if os.path.exists(arduino_device) is False:
			print(f"Arduino: device '{arduino_device}' does not exist", flush=True)
			return False
		while self.serial is None:
			try:
				self.serial = serial.Serial(port=arduino_device, timeout=arduino_timeout, baudrate=arduino_baudrate,
				                            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
				print(f"Arduino: opened '{arduino_device}'", flush=True)
				response = ['application/runtime', {'status': 'booting'}]
				while response[0] != 'application/runtime' or response[1]['status'] == 'booting':
					await self.serial_writeline('["application/runtime", {"status":"?"}]')
					response = json.loads(await self.serial_readline(timeout=1))
				if response[0] == 'application/runtime' and response[1]['status'] == 'configuring':
					#TODO i2c_bus  = configuration.getint('mcp23X17', 'i2c-bus', fallback=0)
					#TODO i2c_addr = configuration.getint('mcp23X17', 'i2c-address', fallback=32)
					await self.serial_writeline('["device/mcp23X17", {"init":{"i2c-bus":%d,"i2c-address":%d}}]' % (0, 32))
					#TODO: device config
					await self.serial_writeline('["device/mcp23X17", {"start":true}]')
					await self.serial_writeline('["", ""]')
					await asyncio.sleep(0.1) # give arduino time to process those commands
					print(f"Arduino: configured '{arduino_device}'", flush=True)
				while response[0] != 'application/runtime' or response[1]['status'] != 'running':
					await self.serial_writeline('["application/runtime", {"status":"?"}]')
					response = json.loads(await self.serial_readline(timeout=1))
				print(f"Arduino: '{arduino_device}' is now up and running, starting command and event listeners", flush=True)
				self.command_task = asyncio.create_task(self.run_command_listener())
				self.event_task   = asyncio.create_task(self.run_event_listener())
			except Exception as e:
				print(f"Arduino: {e}", flush=True)
				self.serial.close()
				self.serial = None
		return True


	async def serial_readline(self, timeout):
		if timeout is not None:
			timeout += time.monotonic()
		line = None
		if self.serial is not None:
			line = ""
			while len(line) == 0:
				chunk = self.serial.readline().decode('utf-8')
				while '\n' not in chunk:
					if timeout is not None and time.monotonic() > timeout:
						return None
					await asyncio.sleep(0.001)
					if len(chunk) > 0:
						line += chunk.strip('\n')
					chunk = self.serial.readline().decode('utf-8')
				line += chunk.strip('\n')
				print(f"Arduino: D->H: {line}", flush=True)
				if len(line) < 8 or line[0] != '[' or line[-1] != ']':
					print(f"Arduino: Skipping over non-webserial message (probably an arduino error message): {line}", flush=True)
					line = ""
		return line


	async def serial_writeline(self, line):
		if self.serial is not None:
			print(f"Arduino: H->D: {line}", flush=True)
			self.serial.write(f'{line}\n'.encode('utf-8'))


	async def run_command_listener(self):
		while True:
			command = await self.commands.get()
			print(f"Arduino: COMMAND={command}", flush=True)
			if command['topic'] == 'status':
				self.events.put_nowait({'topic': 'interface/state', 'payload': 'online'})
			if isinstance(command, dict) and 'topic' in command and 'payload' in command:
				topic = command['topic']
				payload = command['payload']
				if isinstance(payload, str) is True:
					await self.serial_writeline(f'["{topic}", "{payload}"]')
				else:
					await self.serial_writeline(f'["{topic}", {json.dumps(payload)}]')

	async def run_event_listener(self):
		line = await self.serial_readline()
		while line is not None:
			try:
				event = json.loads(line)
				if isinstance(event, list) and len(event) == 2:
					self.events.put_nowait({'topic': event[0], 'payload': event[1]})
				else:
					print(f"Arduino: unexpected (but valid) JSON structure received: {line}", flush=True)
			except Exception as e:
				print(f"Arduino: {e}", flush=True)
			await asyncio.sleep(0.01)
			line = await self.serial_readline()

