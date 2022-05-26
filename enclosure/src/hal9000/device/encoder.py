#!/usr/bin/python3


from configparser import ConfigParser
from gpiozero import InputDevice

from hal9000.device import HAL9000_Device as HAL9000


class Device(HAL9000):

	ROTARY_MODE_POSITION = "position"
	ROTARY_MODE_DELTA = "delta"
	ROTARY_MODES = [ ROTARY_MODE_POSITION, ROTARY_MODE_DELTA ]

	def __init__(self, name: str):
		HAL9000.__init__(self, 'encoder:{}'.format(name))
		self.config = dict()
		self.device = dict()
		self.device['rotary'] = dict()
		self.device['rotary']['data'] = 0x00
		self.device['rotary']['direction'] = 0
		self.device['irq'] = None
		self.driver = None


	def configure(self, configuration: ConfigParser):
		HAL9000.configure(self, configuration)
		peripheral, device = str(self).split(':')
		self.config['enabled'] = configuration.getboolean(str(self), 'enabled', fallback=True)
		if self.config['enabled']:
			Driver = self.load_driver(configuration.get(str(self), 'driver'))
			self.driver = Driver('{}:{}'.format(configuration.get(str(self), 'driver'), device))
			self.driver.configure(configuration)

		self.config['rotary-enabled'] = configuration.getboolean(str(self), 'rotary-enabled', fallback=True)
		if self.config['rotary-enabled']:
			self.config['rotary-pins-sig'] = configuration.getlist(str(self), 'mcp23017-rotary-signal-pins')
			self.config['rotary-pins-gnd'] = configuration.getlist(str(self), 'mcp23017-rotary-ground-pins')
			self.config['rotary-mode'] = configuration.get(str(self), 'rotary-mode', fallback=Device.ROTARY_MODE_POSITION)
			if self.config['rotary-mode'] == Device.ROTARY_MODE_POSITION:
				self.device['rotary-pos'] = configuration.getint(str(self), 'rotary-position-initial', fallback=0)
				self.config['rotary-min'] = configuration.getint(str(self), 'rotary-position-min', fallback=0)
				self.config['rotary-max'] = configuration.getint(str(self), 'rotary-position-max', fallback=100)
				self.config['rotary-step'] = configuration.getint(str(self), 'rotary-position-step', fallback=1)
			for pin in self.config['rotary-pins-sig']:
				self.driver.setup(pin, Driver.IN, Driver.HIGH, Driver.NONINVERT, True, True, True)
			for pin in self.config['rotary-pins-gnd']:
				self.driver.setup(pin, Driver.OUT, Driver.LOW)

		self.config['button-enabled'] = configuration.getboolean(str(self), 'button-enabled', fallback=True)
		if self.config['button-enabled']:
			self.config['button-pins-sig'] = configuration.getlist(str(self), 'mcp23017-button-signal-pins')
			self.config['button-pins-gnd'] = configuration.getlist(str(self), 'mcp23017-button-ground-pins')
			self.device['button-status'] = False
			for pin in self.config['button-pins-sig']:
				self.driver.setup(pin, Driver.IN, Driver.HIGH, Driver.NONINVERT, True, True, True)
			for pin in self.config['button-pins-gnd']:
				self.driver.setup(pin, Driver.OUT, Driver.LOW)
		pin = configuration.getint(str(self), 'gpio-irq', fallback=0)
		if pin > 0:
			self.config['irq-pullup'] = configuration.getboolean(str(self), 'gpio-irq-pullup', fallback=True)
			self.device['irq'] = InputDevice(pin=pin, pull_up=self.config['irq-pullup'])


	def do_loop(self, callback_event = None) -> bool:
		peripheral, device = str(self).split(':')
		irq = self.device['irq']
		if irq is None or irq.value != self.config['irq-pullup']:
			if self.config['rotary-enabled']:
				pin1, pin2 = self.config['rotary-pins-sig']
				value1 = self.driver.input(pin1)
				value2 = self.driver.input(pin2)
				rotary_delta = self.calculate_rotary(value1, value2)
				if rotary_delta != 0:
					event_formatter = '{}'
					if self.config['rotary-mode'] == Device.ROTARY_MODE_DELTA:
						rotary_pos = rotary_delta
						event_formatter = '{0:+}'
					elif self.config['rotary-mode'] == Device.ROTARY_MODE_POSITION:
						rotary_pos = self.device['rotary-pos'] + (rotary_delta * self.config['rotary-step'])
						if rotary_pos < self.config['rotary-min']:
							rotary_pos = self.config['rotary-min']
						if rotary_pos > self.config['rotary-max']:
							rotary_pos = self.config['rotary-max']
						if rotary_pos != self.device['rotary-pos']:
							self.device['rotary-pos'] = rotary_pos
					if callback_event is not None:
						callback_event(peripheral, device, 'rotary', event_formatter.format(rotary_pos))
			if self.config['button-enabled']:
				button_status = False
				for pin in self.config['button-pins-sig']:
					value = self.driver.input(pin)
					button_status |= self.calculate_button(value)
				if button_status != self.device['button-status']:
					self.device['button-status'] = button_status
					if callback_event is not None:
						callback_event(peripheral, device, 'button', str(int(button_status)))
		return True


	def calculate_rotary(self, valA: int, valB: int) -> int:
		rotary_state_data = ((valA&0x01) << 4) + ((valB&0x01) << 0)
		if rotary_state_data != self.device['rotary']['data']:
			rotary_delta = 0
			if self.device['rotary']['data'] == 0x00:
				if rotary_state_data == 0x01:
					self.device['rotary']['direction'] = +1
				elif rotary_state_data == 0x10:
					self.device['rotary']['direction'] = -1
			elif self.device['rotary']['data'] == 0x01:
				if rotary_state_data == 0x11:
					self.device['rotary']['direction'] = +1
				elif rotary_state_data == 0x00:
					if self.device['rotary']['direction'] == -1:
						rotary_delta = -1
			elif self.device['rotary']['data'] == 0x10:
				if rotary_state_data == 0x11:
					self.device['rotary']['direction'] = -1
				elif rotary_state_data == 0x00:
					if self.device['rotary']['direction'] == +1:
						rotary_delta = +1
			else:
				if rotary_state_data == 0x01:
					self.device['rotary']['direction'] = -1
				elif rotary_state_data == 0x10:
					self.device['rotary']['direction'] = +1
				elif rotary_state_data == 0x00:
					if self.device['rotary']['direction'] == -1:
						rotary_delta = -1
					elif self.device['rotary']['direction'] == +1:
						rotary_delta = +1
			self.device['rotary']['data'] = rotary_state_data
			return rotary_delta
		return 0


	def calculate_button(self, value: int) -> bool:
		return bool(not(value))

