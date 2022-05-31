#!/usr/bin/python3


from configparser import ConfigParser
from gpiozero import InputDevice

from hal9000.peripherals.device import HAL9000_Device
from hal9000.peripherals.driver import HAL9000_Driver


class Device(HAL9000_Device):

	def __init__(self, name: str, Driver: HAL9000_Driver):
		HAL9000_Device.__init__(self, 'button:{}'.format(name), Driver)
		self.config = dict()
		self.device = dict()
		self.driver = None


	def configure(self, configuration: ConfigParser, section_name: str = None):
		HAL9000_Device.configure(self, configuration, section_name)
		peripheral, device = str(self).split(':')
		self.config['enabled'] = configuration.getboolean(str(self), 'enabled', fallback=True)
		self.config['count'] = configuration.getint(str(self), 'count', fallback=1)
		if self.config['enabled']:
			self.driver = self.Driver('{}:{}'.format(configuration.getstring(str(self), 'driver'), device))
			self.driver.configure(configuration, section_name)

			self.device['status'] = list()
			for button in range(0, self.config['count']):
				self.device['status'].append(False)
			self.device['name'] = list()
			for button in range(0, self.config['count']):
				key = 'button.{}'.format(button)
				self.device['name'].append(configuration.getstring(str(self), key, fallback=key))


	def do_loop(self, callback_event = None) -> bool:
		if self.driver is not None:
			self.driver.do_loop()
			if callback_event is not None:
				peripheral, device = str(self).split(':')
				for button_number in range(0, self.config['count']):
					driver_data = self.driver.button_data
					button_old = self.device['status'][button_number]
					button_new = self.calculate_button(driver_data[button_number])
					if button_new is not None and button_old != button_new:
						self.device['status'][button_number] = button_new
						callback_event(peripheral, device, self.device['name'][button_number], 'status', int(button_new))
			return True
		return False


	def calculate_button(self, value: int) -> bool:
		return not(bool(value))

