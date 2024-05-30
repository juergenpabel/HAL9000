#!/usr/bin/env python3

from usb import busses as usb_busses
from os.path import exists as os_path_exists
from time import monotonic as time_monotonic
from json import loads as json_loads, dumps as json_dumps
from configparser import ParsingError as configparser_ParsingError
from serial import Serial as serial_Serial, EIGHTBITS as serial_EIGHTBITS, \
                   PARITY_NONE as serial_PARITY_NONE, STOPBITS_ONE as serial_STOPBITS_ONE
from fastapi import FastAPI as fastapi_FastAPI
from asyncio import sleep as asyncio_sleep, create_task as asyncio_create_task

from hal9000.frontend import Frontend

class HAL9000(Frontend):

	def __init__(self, app: fastapi_FastAPI):
		super().__init__()
		self.serial = None

	async def configure(self, filename) -> bool:
		if await super().configure(filename) is False:
			print(f"[frontend:arduino] parsing '{filename}' failed")
			return False
		arduino_device   = self.config.getstring('arduino', 'device',   fallback='/dev/ttyHAL9000')
		arduino_baudrate = self.config.getint   ('arduino', 'baudrate', fallback=115200)
		arduino_timeout  = self.config.getfloat ('arduino', 'timeout',  fallback=0.01)
		if os_path_exists(arduino_device) is False:
			print(f"Arduino: device '{arduino_device}' does not exist", flush=True)
			return False
		while self.serial is None:
			try:
				self.serial = serial_Serial(port=arduino_device, timeout=arduino_timeout, baudrate=arduino_baudrate,
				                            bytesize=serial_EIGHTBITS, parity=serial_PARITY_NONE, stopbits=serial_STOPBITS_ONE)
				print(f"Arduino: opened '{arduino_device}'", flush=True)
				response = ['application/runtime', {'status': 'booting'}]
				while response[0] != 'application/runtime' or response[1]['status'] == 'booting':
					await self.serial_writeline('["application/runtime", {"status":"?"}]')
					response = json_loads(await self.serial_readline(timeout=1))
				if response[0] == 'application/runtime' and response[1]['status'] == 'configuring':
					arduino_name = None
					busses = usb_busses()
					for bus in busses:
						devices = bus.devices
						for device in devices:
							if arduino_name is None:
								arduino_name = self.config.getstring('arduinos', f"{device.idVendor:04x}:{device.idProduct:04x}")
					if arduino_name is not None:
						i2c_bus = self.config.getint(arduino_name, 'i2c-bus', fallback=0)
						i2c_addr = self.config.getint(arduino_name, 'i2c-address', fallback=32)
						await self.serial_writeline('["device/mcp23X17", {"init":{"i2c-bus":%d,"i2c-address":%d}}]' % (i2c_bus, i2c_addr))
						for key in self.config.options(f'{arduino_name}:mcp23X17'):
							value = self.config.getstring(f'{arduino_name}:mcp23X17', key)
							if ':' in key:
								input_type, input_name = key.split(':', 1)
								input_list = value.replace(' ', '').split(',')
								mcp23X17_data = {'config': {'device': {'type': input_type, 'name': input_name, 'inputs': []}}}
								for input in input_list:
									label, pin = input.split(':', 1)
									if input_type == 'button' or input_type == 'switch':
										mcp23X17_data['config']['device']['inputs'].append({'pin': pin, 'label': label, 'pullup': 'true'})
										mcp23X17_data['config']['device']['events'] = {'low': 'on', 'high': 'off'}
									elif input_type == 'rotary':
										mcp23X17_data['config']['device']['inputs'].append({'pin': pin, 'label': label})
									else:
										raise configparser_ParsingError(f"Unknown prefix '{input_type}' in '{arduino_name}:mcp23X17')")
								await self.serial_writeline('["device/mcp23X17", ' + json_dumps(mcp23X17_data) + ']')
							else:
								raise configparser_ParsingError(f"Unsupported item '{key}' in section '{arduino_name}:mcp23X17')")
						await self.serial_writeline('["device/mcp23X17", {"start":true}]')
					await self.serial_writeline('["", ""]')
					print(f"Arduino: configured '{arduino_device}'", flush=True)
				while response[0] != 'application/runtime' or response[1]['status'] != 'running':
					await self.serial_writeline('["application/runtime", {"status":"?"}]')
					response = json_loads(await self.serial_readline(timeout=1))
				print(f"Arduino: '{arduino_device}' is now up and running, starting command and event listeners", flush=True)
				self.command_task = asyncio_create_task(self.run_command_listener())
				self.event_task   = asyncio_create_task(self.run_event_listener())
				self.events.put_nowait({'topic': 'interface/state', 'payload': 'online'})
			except Exception as e:
				print(f"Arduino: {e}", flush=True)
				self.serial.close()
				self.serial = None
		return True


	async def serial_readline(self, timeout):
		if timeout is not None:
			timeout += time_monotonic()
		line = None
		if self.serial is not None:
			line = ""
			while len(line) == 0:
				chunk = self.serial.readline().decode('utf-8')
				while '\n' not in chunk:
					if timeout is not None and time_monotonic() > timeout:
						return None
					await asyncio_sleep(0.001)
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
			if isinstance(command, dict) and 'topic' in command and 'payload' in command:
				topic = command['topic']
				payload = command['payload']
				if isinstance(payload, str) is True:
					await self.serial_writeline(f'["{topic}", "{payload}"]')
				else:
					await self.serial_writeline(f'["{topic}", {json_dumps(payload)}]')


	async def run_event_listener(self):
		line = await self.serial_readline()
		while line is not None:
			try:
				event = json_loads(line)
				if isinstance(event, list) and len(event) == 2:
					self.events.put_nowait({'topic': event[0], 'payload': event[1]})
				else:
					print(f"Arduino: unexpected (but valid) JSON structure received: {line}", flush=True)
			except Exception as e:
				print(f"Arduino: {e}", flush=True)
			await asyncio_sleep(0.01)
			line = await self.serial_readline()

