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

import logging
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
				response = ['application/runtime', {'status': 'starting'}]
				while response[0] != 'application/runtime' or 'status' not in response[1] or response[1]['status'] == 'starting':
					await self.serial_writeline('["application/runtime", {"status":"?"}]')
					await asyncio_sleep(0.5)
					line = await self.serial_readline(timeout=0.5)
					if line is not None:
						response = json_loads(line)
				logging_getLogger('uvicorn').debug(f"[frontend:arduino] MCU exited status 'starting' (now: '{response[1]['status']}')") 
				if response[0] == 'application/runtime' and 'status' in response[1] and response[1]['status'] == 'configuring':
					arduino_name = None
					for bus in usb_busses():
						for device in bus.devices:
							arduino_name = configuration.get('arduinos', f'{device.idVendor:04x}:{device.idProduct:04x}', fallback=arduino_name)
					if arduino_name is not None:
						i2c_bus = configuration.getint(arduino_name, 'i2c-bus', fallback=0)
						i2c_addr = configuration.getint(arduino_name, 'i2c-address', fallback=32)
						await self.serial_writeline('["device/mcp23X17", {"init":{"i2c-bus":%d,"i2c-address":%d}}]' % (i2c_bus, i2c_addr))
						await asyncio_sleep(0.5)
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
								await asyncio_sleep(0.5)
							else:
								raise configparser_ParsingError(f"Unsupported item '{key}' in section '{arduino_name}:mcp23X17')")
						await self.serial_writeline('["device/mcp23X17", {"start":true}]')
						await asyncio_sleep(0.5)
					await self.serial_writeline('["", ""]')
					await asyncio_sleep(0.5)
					logging_getLogger('uvicorn').info(f"[frontend:arduino] configured '{arduino_device}'")
				while response[0] != 'application/runtime' or 'status' not in response[1] or response[1]['status'] == 'configuring':
					await asyncio_sleep(0.5)
					line = None
					while line is None:
						line = await self.serial_readline(timeout=0.5)
					response = json_loads(line)
				logging_getLogger('uvicorn').debug(f"[frontend:arduino] MCU exited status 'configuring' (now: '{response[1]['status']}')") 
				if response[1]['status'] == 'waiting':
					await self.serial_writeline('["application/environment", {"set":{"key": "gui/screen:animations/loop", "value": "false"}}]')
				while response[0] != 'application/runtime' or 'status' not in response[1] or response[1]['status'] != 'running':
					line = None
					while line is None:
						line = await self.serial_readline(timeout=1.0)
					response = json_loads(line)
				logging_getLogger('uvicorn').debug(f"[frontend:arduino] MCU entered status 'running'")
				logging_getLogger('uvicorn').info(f"[frontend:arduino] '{arduino_device}' is now up and running")
			except (configparser_ParsingError, serial_SerialException) as e:
				logging_getLogger('uvicorn').error(f"[frontend:arduino] {e}")
				if self.serial is not None:
					self.serial.close()
					self.serial = None
				return False

		return True


	async def start(self) -> None:
		await super().start()
		self.h2d_task = asyncio_create_task(self.task_host2device())
		self.d2h_task   = asyncio_create_task(self.task_device2host())


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


	async def task_host2device(self):
		logging_getLogger('uvicorn').info(f"[frontend:arduino] starting host2device-listener")
		while os_path_exists(self.serial.port):
			if self.serial.is_open is False:
				self.serial.open()
				await asyncio_sleep(1)
			try:
				while self.serial.is_open is True:
					if self.status != Frontend.FRONTEND_STATUS_ONLINE:
						self.status = Frontend.FRONTEND_STATUS_ONLINE
						logging_getLogger('uvicorn').info(f"[frontend:arduino] task_host2device() changed status to 'online'")
						self.events.put_nowait({'topic': 'status', 'payload': self.status})
						self.commands.put_nowait(None) # to wake up task_host2device()
					command = await self.commands.get()
					logging_getLogger('uvicorn').debug(f"[frontend:arduino] received command: {command}")
					if isinstance(command, dict) and 'topic' in command and 'payload' in command:
						topic = command['topic']
						payload = command['payload']
						if isinstance(payload, str) is True:
							await self.serial_writeline(f'["{topic}", "{payload}"]')
						else:
							await self.serial_writeline(f'["{topic}", {json_dumps(payload)}]')
				logging_getLogger('uvicorn').debug(f"[frontend:arduino] serial device '{self.serial.port}' (unexpectedly) closed")
			except Exception as e:
				logging_getLogger('uvicorn').error(f"[frontend:arduino] exception in task_host2device(): {e}")
			self.status = Frontend.FRONTEND_STATUS_OFFLINE
			logging_getLogger('uvicorn').info(f"[frontend:arduino] task_host2device() changed status to 'offline'")
			self.events.put_nowait({'topic': 'status', 'payload': self.status})
			self.commands.put_nowait(None) # to wake up task_host2device()
		logging_getLogger('uvicorn').error(f"[frontend:arduino] exiting host2device-listener ('arduino' frontend becomes non-functional)")


	async def task_device2host(self):
		logging_getLogger('uvicorn').info(f"[frontend:arduino] starting device2host-listener")
		while os_path_exists(self.serial.port):
			if self.serial.is_open is False:
				self.serial.open()
				await asyncio_sleep(1)
			try:
				while self.serial.is_open is True:
					if self.status != Frontend.FRONTEND_STATUS_ONLINE:
						self.status = Frontend.FRONTEND_STATUS_ONLINE
						logging_getLogger('uvicorn').info(f"[frontend:arduino] task_device2host() changed status to 'online'")
						self.events.put_nowait({'topic': 'status', 'payload': self.status})
						self.commands.put_nowait(None) # to wake up task_host2device()
					line = await self.serial_readline()
					try:
						event = json_loads(line)
						if isinstance(event, list) and len(event) == 2:
							if event[0].startswith('syslog/'):
								if hasattr(logging, event[0][7:].upper()) is True:
									logging_getLogger('uvicorn').log(getattr(logging, event[0][7:].upper()), json_dumps(event[1]))
							self.events.put_nowait({'topic': event[0], 'payload': event[1]})
						else:
							logging_getLogger('uvicorn').warning(f"[frontend:arduino] unexpected (but valid) JSON structure received: {line}")
					except Exception as e:
						logging_getLogger('uvicorn').error(f"[frontend:arduino] {e}")
					await asyncio_sleep(0.01)
				logging_getLogger('uvicorn').debug(f"[frontend:arduino] serial device '{self.serial.port}' (unexpectedly) closed")
			except Exception as e:
				logging_getLogger('uvicorn').error(f"[frontend:arduino] exception in task_device2host(): {e}")
			self.status = Frontend.FRONTEND_STATUS_OFFLINE
			logging_getLogger('uvicorn').info(f"[frontend:arduino] task_device2host() changed status to 'offline'")
			self.events.put_nowait({'topic': 'status', 'payload': self.status})
			self.commands.put_nowait(None) # to wake up task_host2device()
		logging_getLogger('uvicorn').error(f"[frontend:arduino] exiting device2host-listener ('arduino' frontend becomes non-functional)")

