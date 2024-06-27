#!/usr/bin/env python3

from os.path import exists as os_path_exists
from time import monotonic as time_monotonic
from json import loads as json_loads, dumps as json_dumps
from configparser import ParsingError as configparser_ParsingError
from logging import getLogger as logging_getLogger
from serial import Serial as serial_Serial, EIGHTBITS as serial_EIGHTBITS, \
                   PARITY_NONE as serial_PARITY_NONE, STOPBITS_ONE as serial_STOPBITS_ONE, \
                   SerialException as serial_SerialException
from asyncio import sleep as asyncio_sleep, create_task as asyncio_create_task
from usb import busses as usb_busses

from fastapi import FastAPI as fastapi_FastAPI

from hal9000.frontend import Frontend


class HAL9000(Frontend):

	def __init__(self, app: fastapi_FastAPI):
		super().__init__()
		self.serial = None


	async def configure(self, configuration) -> bool:
		arduino_device   = configuration.getstring('arduino', 'device',   fallback='/dev/ttyHAL9000')
		arduino_baudrate = configuration.getint   ('arduino', 'baudrate', fallback=115200)
		arduino_timeout  = configuration.getfloat ('arduino', 'timeout',  fallback=0.01)
		if os_path_exists(arduino_device) is False:
			logging_getLogger('uvicorn').info(f"[frontend:arduino] configured device '{arduino_device}' does not exist")
			return None
		while self.serial is None:
			try:
				self.serial = serial_Serial(port=arduino_device, timeout=arduino_timeout, baudrate=arduino_baudrate,
				                            bytesize=serial_EIGHTBITS, parity=serial_PARITY_NONE, stopbits=serial_STOPBITS_ONE)
				logging_getLogger('uvicorn').info(f"[frontend:arduino] opened '{arduino_device}'")
				response = ['application/runtime', {'status': 'booting'}]
				while response[0] != 'application/runtime' or response[1]['status'] == 'booting':
					await self.serial_writeline('["application/runtime", {"status":"?"}]')
					line = await self.serial_readline(timeout=1)
					if line is not None:
						response = json_loads(line)
				if response[0] == 'application/runtime' and response[1]['status'] == 'configuring':
					arduino_name = None
					for bus in usb_busses():
						for device in bus.devices:
							arduino_name = configuration.get('arduinos', f'{device.idVendor:04x}:{device.idProduct:04x}', fallback=arduino_name)
					if arduino_name is not None:
						i2c_bus = configuration.getint(arduino_name, 'i2c-bus', fallback=0)
						i2c_addr = configuration.getint(arduino_name, 'i2c-address', fallback=32)
						await self.serial_writeline('["device/mcp23X17", {"init":{"i2c-bus":%d,"i2c-address":%d}}]' % (i2c_bus, i2c_addr))
						for key in configuration.options(f'{arduino_name}:mcp23X17'):
							if ':' in key:
								input_type, input_name = key.split(':', 1)
								input_list = configuration.getlist(f'{arduino_name}:mcp23X17', key)
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
					logging_getLogger('uvicorn').info(f"[frontend:arduino] configured '{arduino_device}'")
				while response[0] != 'application/runtime' or response[1]['status'] != 'running':
					await self.serial_writeline('["application/runtime", {"status":"?"}]')
					line = None
					while line is None:
						line = await self.serial_readline(timeout=1)
					response = json_loads(line)
				logging_getLogger('uvicorn').info(f"[frontend:arduino] '{arduino_device}' is now up and running")
				self.command_task = asyncio_create_task(self.run_command_listener())
				self.event_task   = asyncio_create_task(self.run_event_listener())
			except (configparser_ParsingError, serial_SerialException) as e:
				logging_getLogger('uvicorn').error(f"[frontend:arduino] {e}")
				if self.serial is not None:
					self.serial.close()
					self.serial = None
				return False

		return True


	async def serial_readline(self, timeout=None):
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
				logging_getLogger('uvicorn').debug(f"[frontend:arduino] D->H: {line}")
				if len(line) < 8 or line[0] != '[' or line[-1] != ']':
					logging_getLogger('uvicorn').warning(f"[frontend:arduino] skipping over non-webserial message (probably an arduino error message): {line}")
					line = ""
		return line


	async def serial_writeline(self, line):
		if self.serial is not None:
			logging_getLogger('uvicorn').debug(f"[frontend:arduino] H->D: {line}")
			self.serial.write(f'{line}\n'.encode('utf-8'))


	async def run_command_listener(self):
		logging_getLogger('uvicorn').info(f"[frontend:arduino] starting command-listener")
		try:
			while self.serial.is_open is True and os_path_exists(self.serial.port):
				command = await self.commands.get()
				logging_getLogger('uvicorn').debug(f"[frontend:arduino] received command: {command}")
				if isinstance(command, dict) and 'topic' in command and 'payload' in command:
					topic = command['topic']
					payload = command['payload']
					if isinstance(payload, str) is True:
						await self.serial_writeline(f'["{topic}", "{payload}"]')
					else:
						await self.serial_writeline(f'["{topic}", {json_dumps(payload)}]')
		except Exception as e:
			logging_getLogger('uvicorn').error(f"[frontend:arduino] exception in run_command_listener(): {e}")
		logging_getLogger('uvicorn').error(f"[frontend:arduino] exiting command-listener ('arduino' frontend becomes non-functional)")


	async def run_event_listener(self):
		logging_getLogger('uvicorn').info(f"[frontend:arduino] starting event-listener")
		self.events.put_nowait({'topic': 'status', 'payload': 'online'})
		try:
			while self.serial.is_open is True:
				line = await self.serial_readline()
				try:
					event = json_loads(line)
					if isinstance(event, list) and len(event) == 2:
						self.events.put_nowait({'topic': event[0], 'payload': event[1]})
					else:
						logging_getLogger('uvicorn').warning(f"[frontend:arduino] unexpected (but valid) JSON structure received: {line}")
				except Exception as e:
					logging_getLogger('uvicorn').error(f"[frontend:arduino] {e}")
				await asyncio_sleep(0.01)
		except Exception as e:
			logging_getLogger('uvicorn').error(f"[frontend:arduino] exception in run_event_listener(): {e}")
		logging_getLogger('uvicorn').error(f"[frontend:arduino] exiting event-listener ('arduino' frontend becomes non-functional)")
		self.commands.put_nowait(None) # to wake up run_command_listener()

