#!/usr/bin/python3


from configparser import ConfigParser
from gpiozero import InputDevice

from hal9000.device import HAL9000_Device as HAL9000

from hal9000.driver.mcp23017 import MCP23017 as Driver


class Device(HAL9000):

	ROTARY_MODE_POSITION = "position"
	ROTARY_MODE_DELTA = "delta"
	ROTARY_MODES = [ ROTARY_MODE_POSITION, ROTARY_MODE_DELTA ]

	def __init__(self, name: str):
		HAL9000.__init__(self, 'rotary:{}'.format(name))
		self.driver = Driver('mcp23017:{}'.format(name))
		self.button = dict()
		self.rotary = dict()
		self.rotary['internal'] = dict()
		self.rotary['internal']['data'] = 0x00
		self.rotary['internal']['direction'] = 0
		self.gpio = dict()
		self.gpio['irq'] = None


	def configure(self, configuration: ConfigParser):
		HAL9000.configure(self, configuration)
		self.rotary['enabled'] = configuration.getboolean(str(self), 'rotary-enabled', fallback=True)
		if self.rotary['enabled']:
			self.rotary['pins-sig'] = configuration.getlist(str(self), 'mcp23017-rotary-signal-pins')
			self.rotary['pins-gnd'] = configuration.getlist(str(self), 'mcp23017-rotary-ground-pins')
			self.rotary['mode'] = configuration.get(str(self), 'rotary-mode', fallback=Device.ROTARY_MODE_POSITION)
			if self.rotary['mode'] == Device.ROTARY_MODE_POSITION:
				self.rotary['pos'] = configuration.getint(str(self), 'rotary-position-initial', fallback=0)
				self.rotary['min'] = configuration.getint(str(self), 'rotary-position-min', fallback=0)
				self.rotary['max'] = configuration.getint(str(self), 'rotary-position-max', fallback=100)
				self.rotary['step'] = configuration.getint(str(self), 'rotary-position-step', fallback=1)
		self.button['enabled'] = configuration.getboolean(str(self), 'button-enabled', fallback=True)
		if self.button['enabled']:
			self.button['pins-sig'] = configuration.getlist(str(self), 'mcp23017-button-signal-pins')
			self.button['pins-gnd'] = configuration.getlist(str(self), 'mcp23017-button-ground-pins')
			self.button['status'] = False
		pin = configuration.getint(str(self), 'gpio-irq', fallback=0)
		if pin > 0:
			self.gpio['irq-pullup'] = configuration.getboolean(str(self), 'gpio-irq-pullup', fallback=True)
			self.gpio['irq'] = InputDevice(pin=pin, pull_up=self.gpio['irq-pullup'])
		self.driver.configure(configuration)
		if self.rotary['enabled']:
			for pin in self.rotary['pins-sig']:
				self.driver.setup(pin, Driver.IN, Driver.HIGH, Driver.NONINVERT, True, True, True)
			for pin in self.rotary['pins-gnd']:
				self.driver.setup(pin, Driver.OUT, Driver.LOW)
		if self.button['enabled']:
			for pin in self.button['pins-sig']:
				self.driver.setup(pin, Driver.IN, Driver.HIGH, Driver.NONINVERT, True, True, True)
			for pin in self.button['pins-gnd']:
				self.driver.setup(pin, Driver.OUT, Driver.LOW)


	def do_loop(self, callback_rotary = None, callback_button = None) -> bool:
		irq = self.gpio['irq']
		if irq is None or irq.value != self.gpio['irq-pullup']:
			if self.rotary['enabled']:
				pin1, pin2 = self.rotary['pins-sig']
				val1 = self.driver.input(pin1)
				val2 = self.driver.input(pin2)
				rotary_delta = self.calculate_rotary(val1, val2)
				if rotary_delta != 0:
					if self.rotary['mode'] == Device.ROTARY_MODE_DELTA:
						if callback_rotary is not None:
							callback_rotary(rotary_delta)
					else:
						rotary_pos = self.rotary['pos'] + (rotary_delta * self.rotary['step'])
						if rotary_pos < self.rotary['min']:
							rotary_pos = self.rotary['min']
						if rotary_pos > self.rotary['max']:
							rotary_pos = self.rotary['max']
						if rotary_pos != self.rotary['pos']:
							self.rotary['pos'] = rotary_pos
							if callback_rotary is not None:
								callback_rotary(rotary_pos)
			if self.button['enabled']:
				button_status = False
				for pin in self.button['pins-sig']:
					button_status |= bool(not(self.driver.input(pin)))
				if button_status != self.button['status']:
					self.button['status'] = button_status
					if callback_button is not None:
						callback_button(self.button['status'])
		return True


	def calculate_rotary(self, valA: int, valB: int) -> int:
		rotary_state_data = ((valA&0x01) << 4) + ((valB&0x01) << 0)
		if rotary_state_data != self.rotary['internal']['data']:
			rotary_delta = 0
			if self.rotary['internal']['data'] == 0x00:
				if rotary_state_data == 0x01:
					self.rotary['internal']['direction'] = +1
				elif rotary_state_data == 0x10:
					self.rotary['internal']['direction'] = -1
			elif self.rotary['internal']['data'] == 0x01:
				if rotary_state_data == 0x11:
					self.rotary['internal']['direction'] = +1
				elif rotary_state_data == 0x00:
					if self.rotary['internal']['direction'] == -1:
						rotary_delta = -1
			elif self.rotary['internal']['data'] == 0x10:
				if rotary_state_data == 0x11:
					self.rotary['internal']['direction'] = -1
				elif rotary_state_data == 0x00:
					if self.rotary['internal']['direction'] == +1:
						rotary_delta = +1
			else:
				if rotary_state_data == 0x01:
					self.rotary['internal']['direction'] = -1
				elif rotary_state_data == 0x10:
					self.rotary['internal']['direction'] = +1
				elif rotary_state_data == 0x00:
					if self.rotary['internal']['direction'] == -1:
						rotary_delta = -1
					elif self.rotary['internal']['direction'] == +1:
						rotary_delta = +1
			self.rotary['internal']['data'] = rotary_state_data
			return rotary_delta
		return 0

