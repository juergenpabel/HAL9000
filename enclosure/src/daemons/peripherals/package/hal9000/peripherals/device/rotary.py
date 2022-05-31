#!/usr/bin/python3


from configparser import ConfigParser
from gpiozero import InputDevice

from hal9000.peripherals.device import HAL9000_Device
from hal9000.peripherals.driver import HAL9000_Driver


class Device(HAL9000_Device):

	def __init__(self, name: str, Driver: HAL9000_Driver):
		HAL9000_Device.__init__(self, 'rotary:{}'.format(name), Driver)
		self.config = dict()
		self.device = dict()
		self.device['encoder'] = dict()
		self.device['encoder']['data'] = 0x00
		self.device['encoder']['direction'] = 0
		self.device['irq'] = None
		self.driver = None


	def configure(self, configuration: ConfigParser, section_name: str = None):
		HAL9000_Device.configure(self, configuration, section_name)
		peripheral, device = str(self).split(':')
		self.config['enabled'] = configuration.getboolean(str(self), 'enabled', fallback=True)
		if self.config['enabled']:
			self.driver = self.Driver('{}:{}'.format(configuration.getstring(str(self), 'driver'), device))
			self.driver.configure(configuration, section_name)

			driver_irq_pin = configuration.getint(str(self), 'driver-irq-pin', fallback=0)
			if driver_irq_pin > 0:
				self.config['driver-irq-pin'] = driver_irq_pin
				self.device['irq'] = InputDevice(pin=driver_irq_pin, pull_up=True)


	def do_loop(self, callback_event = None) -> bool:
		if self.driver is not None:
			peripheral, device = str(self).split(':')
			if self.device['irq'] is None or self.device['irq'].value == 0:
				#TODO: reset irq on driver
				rotary_direction = self.calculate_direction(self.driver.rotary_data)
				if rotary_direction != 0:
					if callback_event is not None:
						callback_event(peripheral, device, None, 'status', '{0:+}'.format(rotary_direction))
			return True
		return False


	def calculate_direction(self, input: list) -> int:
		if len(input) != 2:
			#TODO error
			return 0
		encoder_state_data = ((int(input[0])&0x01) << 4) + ((int(input[1])&0x01) << 0)
		if encoder_state_data != self.device['encoder']['data']:
			encoder_direction = 0
			if self.device['encoder']['data'] == 0x00:
				if encoder_state_data == 0x01:
					self.device['encoder']['direction'] = +1
				elif encoder_state_data == 0x10:
					self.device['encoder']['direction'] = -1
			elif self.device['encoder']['data'] == 0x01:
				if encoder_state_data == 0x11:
					self.device['encoder']['direction'] = +1
				elif encoder_state_data == 0x00:
					if self.device['encoder']['direction'] == -1:
						encoder_direction = -1
			elif self.device['encoder']['data'] == 0x10:
				if encoder_state_data == 0x11:
					self.device['encoder']['direction'] = -1
				elif encoder_state_data == 0x00:
					if self.device['encoder']['direction'] == +1:
						encoder_direction = +1
			else:
				if encoder_state_data == 0x01:
					self.device['encoder']['direction'] = -1
				elif encoder_state_data == 0x10:
					self.device['encoder']['direction'] = +1
				elif encoder_state_data == 0x00:
					if self.device['encoder']['direction'] == -1:
						encoder_direction = -1
					elif self.device['encoder']['direction'] == +1:
						encoder_direction = +1
			self.device['encoder']['data'] = encoder_state_data
			return encoder_direction
		return 0

