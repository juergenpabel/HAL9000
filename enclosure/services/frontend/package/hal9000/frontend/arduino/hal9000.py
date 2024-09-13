from os.path import exists as os_path_exists
from time import monotonic as time_monotonic
from json import loads as json_loads, dumps as json_dumps
from configparser import ConfigParser as configparser_ConfigParser, \
                         ParsingError as configparser_ParsingError
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

	def __init__(self, app: fastapi_FastAPI) -> None:
		super().__init__('arduino')
		self.serial = None
		self.serial_chunk = bytearray(b'')


	async def configure(self, configuration: configparser_ConfigParser) -> bool:
		arduino_device   = configuration.getstring('frontend:arduino', 'device',   fallback=None)
		arduino_baudrate = configuration.getint   ('frontend:arduino', 'baudrate', fallback=115200)
		arduino_timeout  = configuration.getfloat ('frontend:arduino', 'timeout',  fallback=0.01)
		arduino_config   = configuration.getstring('frontend:arduino', 'configuration', fallback='littlefs')
		if arduino_device is None:
			logging_getLogger('uvicorn').info(f"[frontend:arduino] no device configured (section 'frontend:arduino', option 'device' in frontend.ini)")
			return None
		if os_path_exists(arduino_device) is False:
			logging_getLogger('uvicorn').error(f"[frontend:arduino] configured device '{arduino_device}' does not exist")
			return None
		if arduino_config in ['littlefs', 'frontend']:
			logging_getLogger('uvicorn').info(f"[frontend:arduino] using '{arduino_config}' as configuration-source for arduino application")
		else:
			logging_getLogger('uvicorn').warning(f"[frontend:arduino] unsupported value for 'configuration' in section 'frontend:arduino': " \
			                                     f"'{arduino_config}' (falling back to 'littlefs')")
		while self.serial is None:
			try:
				arduino_name = None
				for bus in usb_busses():
					for device in bus.devices:
						arduino_name = configuration.get('arduino:devices', f'{device.idVendor:04x}:{device.idProduct:04x}', fallback=arduino_name)
				if arduino_name is not None:
					logging_getLogger('uvicorn').info(f"[frontend:arduino] identified /dev/ttyHAL9000 as '{arduino_name}'")
				else:
					logging_getLogger('uvicorn').warning(f"[frontend:arduino] unidentified board on /dev/ttyHAL9000 " \
					                                     f"(application configuration only loadable from littlefs)")
				self.serial = serial_Serial(port=arduino_device, timeout=arduino_timeout, baudrate=arduino_baudrate,
				                            bytesize=serial_EIGHTBITS, parity=serial_PARITY_NONE, stopbits=serial_STOPBITS_ONE)
				logging_getLogger('uvicorn').debug(f"[frontend:arduino] opened '{arduino_device}'")
				await self.serial_writeline('["application/runtime", {"status":"?"}]')
				response = ['application/runtime', {'status': {'name': 'starting'}}]
				while response[0] != 'application/runtime' \
				    or 'status' not in response[1] or 'name' not in response[1]['status'] \
				    or response[1]['status']['name'] == 'starting':
					await asyncio_sleep(0.5)
					line = await self.serial_readline(timeout=0.5)
					if line is not None:
						try:
							response = json_loads(line)
						except Exception as e:
							logging_getLogger('uvicorn').info(f"[frontend:arduino] ignoring line with unexpected format: {line}")
				if response[1]['status']['name'] == 'configuring':
					logging_getLogger('uvicorn').debug(f"[frontend:arduino] application status is now 'configuring'")
					if arduino_config == 'frontend' and arduino_name is not None:
						i2c_bus = configuration.getint(f'arduino:{arduino_name}', 'i2c-bus', fallback=0)
						i2c_addr = configuration.getint(f'arduino:{arduino_name}', 'i2c-address', fallback=32)
						await self.serial_writeline('["device/mcp23X17", {"init":{"i2c-bus":%d,"i2c-address":%d}}]' % (i2c_bus, i2c_addr))
						await asyncio_sleep(0.5)
						for key in configuration.options(f'arduino:{arduino_name}:mcp23X17'):
							if ':' in key:
								input_type, input_name = key.split(':', 1)
								input_list = configuration.getlist(f'arduino:{arduino_name}:mcp23X17', key)
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
						logging_getLogger('uvicorn').debug(f"[frontend:arduino] '{arduino_device}' is now configured via frontend-configuration")
					await self.serial_writeline('["", ""]')
					await asyncio_sleep(0.5)
				while response[0] != 'application/runtime' \
				   or response[1] is False or 'status'  not in response[1] \
				                           or 'name'    not in response[1]['status'] \
				                           or 'configuring' == response[1]['status']['name']:
					await self.serial_writeline('["application/runtime", {"status":"?"}]')
					await asyncio_sleep(0.5)
					line = None
					while line is None:
						line = await self.serial_readline(timeout=0.5)
					try:
						response = json_loads(line)
						if response[0] == 'ping':
							await self.serial_writeline('["pong", ""]')
					except Exception as e:
						logging_getLogger('uvicorn').info(f"[frontend:arduino] ignoring line with unexpected format: {line}")
				if response[1]['status']['name'] == 'waiting':
					logging_getLogger('uvicorn').debug(f"[frontend:arduino] application status is now 'waiting'")
					await self.serial_writeline('["application/environment", {"set":{"key": "gui/screen:animations/loop", "value": "false"}}]')
				if response[1]['status']['name'] == 'panicing':
					error = 'no error details provided'
					if 'error' in response[1]['status']:
						try:
							error = json_loads(response[1]['status']['error'])
						except:
							pass
					logging_getLogger('uvicorn').critical(f"[frontend:arduino] application status is now 'panicing': {error}")
					self.serial.close()
					self.serial = None
					return False
				while response[0] != 'application/runtime' \
				   or response[1] is False or 'status' not in response[1] \
				                           or 'name' not in response[1]['status'] \
				                           or 'running' != response[1]['status']['name']:
					line = None
					while line is None:
						line = await self.serial_readline(timeout=1.0)
					try:
						response = json_loads(line)
						if response[0] == 'ping':
							await self.serial_writeline('["pong", ""]')
					except Exception as e:
						logging_getLogger('uvicorn').info(f"[frontend:arduino] ignoring line with unexpected format: {line}")
				logging_getLogger('uvicorn').debug(f"[frontend:arduino] application status is now 'running'")
			except (configparser_ParsingError, serial_SerialException) as e:
				logging_getLogger('uvicorn').error(f"[frontend:arduino] {e}")
				if self.serial is not None:
					self.serial.close()
					self.serial = None
				return False

		return True


	async def start(self) -> None:
		await super().start()
		self.tasks['host2device'] = asyncio_create_task(self.task_host2device())
		self.tasks['device2host'] = asyncio_create_task(self.task_device2host())


	async def serial_readline(self, timeout: float = 0) -> None:
		if timeout > 0:
			timeout += time_monotonic()
		chunk = b''
		while b'\n' not in chunk:
			if timeout > 0 and time_monotonic() > timeout:
				return None
			if self.serial is None or self.serial.is_open is False:
				return None
			chunk = self.serial.readline()
			if len(chunk) > 0:
				self.serial_chunk.extend(chunk)
			else:
				await asyncio_sleep(0.001)
		line = None
		while line is None:
			try:
				line = self.serial_chunk.decode('utf-8').strip('\n')
			except UnicodeDecodeError as e:
				invalid_chunk = bytearray(b'')
				if e.end >= 0 and e.end < len(self.serial_chunk):
					invalid_chunk = self.serial_chunk[0:e.end]
					self.serial_chunk = self.serial_chunk[e.end:-1]
				else:
					invalid_chunk = self.serial_chunk
					line = ''
				logging_getLogger('uvicorn').warning(f"[frontend:arduino] dropping part of received line due to utf-8 decoding issue: {invalid_chunk}")
		logging_getLogger('uvicorn').log(Frontend.LOG_LEVEL_TRACE, f"[frontend:arduino] D->H: {line}")
		self.serial_chunk = bytearray(b'')
		if isinstance(line, str) is True and (len(line) < 8 or line[0] != '[' or line[-1] != ']'):
			logging_getLogger('uvicorn').warning(f"[frontend:arduino] skipping over non-webserial message (probably an arduino error message): {line}")
			line = None
		return line


	async def serial_writeline(self, line: str) -> None:
		if self.serial is None or self.serial.is_open is not True:
			logging_getLogger('uvicorn').error(f"[frontend:arduino] serial_writeline('{line}') failed as serial connection is not established")
			return
		logging_getLogger('uvicorn').log(Frontend.LOG_LEVEL_TRACE, f"[frontend:arduino] H->D: {line}")
		self.serial.write(f'{line}\n'.encode('utf-8'))


	async def task_host2device(self) -> None:
		logging_getLogger('uvicorn').debug(f"[frontend:arduino] starting host2device-listener")
		while os_path_exists(self.serial.port) and self.tasks['host2device'].cancelled() is False:
			if self.serial.is_open is False:
				self.serial.open()
				await asyncio_sleep(1)
			try:
				if self.runlevel != Frontend.FRONTEND_RUNLEVEL_RUNNING:
					self.runlevel = Frontend.FRONTEND_RUNLEVEL_RUNNING
				while self.serial.is_open is True and self.tasks['host2device'].cancelled() is False:
					if self.status != Frontend.FRONTEND_STATUS_ONLINE:
						self.status = Frontend.FRONTEND_STATUS_ONLINE
					command = await self.commands.get()
					logging_getLogger('uvicorn').debug(f"[frontend:arduino] host2device sends message: {command}")
					if isinstance(command, dict) and 'topic' in command and 'payload' in command:
						topic = command['topic']
						payload = command['payload']
						if isinstance(payload, str) is True:
							await self.serial_writeline(f'["{topic}", "{payload}"]')
						else:
							await self.serial_writeline(f'["{topic}", {json_dumps(payload)}]')
				logging_getLogger('uvicorn').warning(f"[frontend:arduino] serial device '{self.serial.port}' (unexpectedly) closed")
			except Exception as e:
				logging_getLogger('uvicorn').error(f"[frontend:arduino] exception in task_host2device(): {e}")
			self.status = Frontend.FRONTEND_STATUS_OFFLINE
			self.commands.put_nowait(None) # to wake up task_host2device()
		logging_getLogger('uvicorn').error(f"[frontend:arduino] exiting host2device-listener ('arduino' frontend becomes non-functional)")
		del self.tasks['host2device']


	async def task_device2host(self) -> None:
		logging_getLogger('uvicorn').debug(f"[frontend:arduino] starting device2host-listener")
		while os_path_exists(self.serial.port) and self.tasks['device2host'].cancelled() is False:
			if self.serial.is_open is False:
				self.serial.open()
				await asyncio_sleep(1)
			try:
				if self.runlevel != Frontend.FRONTEND_RUNLEVEL_RUNNING:
					self.runlevel = Frontend.FRONTEND_RUNLEVEL_RUNNING
				while self.serial.is_open is True and self.tasks['device2host'].cancelled() is False:
					if self.status != Frontend.FRONTEND_STATUS_ONLINE:
						self.status = Frontend.FRONTEND_STATUS_ONLINE
						self.commands.put_nowait(None) # to wake up task_host2device()
					line = await self.serial_readline()
					try:
						event = json_loads(line)
						if isinstance(event, list) and len(event) == 2:
							logging_getLogger('uvicorn').debug(f"[frontend:arduino] device2host reads message: " + \
							                                   str({'topic': event[0], 'payload': event[1]}))
							if event[0] == 'ping':
								self.commands.put_nowait({'topic': 'pong', 'payload': ''})
								event[0] = ''
							if event[0].startswith('syslog/'):
								log_level = event[0][7:].upper()
								if hasattr(logging, log_level) is True:
									logging_getLogger('uvicorn').log(getattr(logging, log_level),
									                                 f"[frontend:arduino] {event[0]}: {json_dumps(event[1])}")
							if isinstance(event[1], dict) is True:
								if 'origin' not in event[1]:
									event[1]['origin'] = 'frontend:arduino'
							if event[0] != '':
								self.events.put_nowait({'topic': event[0], 'payload': event[1]})
						else:
							logging_getLogger('uvicorn').warning(f"[frontend:arduino] unexpected (but valid) JSON structure received: {line}")
					except Exception as e:
						logging_getLogger('uvicorn').error(f"[frontend:arduino] {e}")
					await asyncio_sleep(0.01)
				logging_getLogger('uvicorn').warning(f"[frontend:arduino] serial device '{self.serial.port}' (unexpectedly) closed")
			except Exception as e:
				logging_getLogger('uvicorn').error(f"[frontend:arduino] exception in task_device2host(): {e}")
			self.status = Frontend.FRONTEND_STATUS_OFFLINE
			self.commands.put_nowait(None) # to wake up task_host2device()
		logging_getLogger('uvicorn').error(f"[frontend:arduino] exiting device2host-listener ('arduino' frontend becomes non-functional)")
		del self.tasks['device2host']

