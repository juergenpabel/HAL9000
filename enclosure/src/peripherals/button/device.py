#!/usr/bin/python3


from configparser import ConfigParser
from gpiozero import InputDevice

from hal9000.device import HAL9000_Device as HAL9000

from hal9000.driver.pcf8591 import PCF8591 as Driver


class Device(HAL9000):

	def __init__(self, name: str):
		HAL9000.__init__(self, 'button:{}'.format(name))
		self.button = dict()
		self.driver = None


	def configure(self, configuration: ConfigParser):
		HAL9000.configure(self, configuration)
		peripheral, device = str(self).split(':')
		self.button['enabled'] = configuration.getboolean(str(self), 'button-enabled', fallback=True)
		if self.button['enabled']:
			self.button['status'] = array()
			for button in range(0, 3):
				self.button['status'][button] = False
			self.driver = Driver('{}:{}'.format(configuration.get(str(self), 'driver'), device))
			self.driver.configure(configuration)


	def do_loop(self, callback_event = None) -> bool:
		if self.driver is not None:
			peripheral, device = str(self).split(':')
			self.driver.do_loop()
			for button in range(0, 3):
				level = self.driver.channel(button)
				self.button['status'][button] = self.calculate_button(level)
		return True


	def calculate_button(self, value: byte) -> bool:
		if value > 0:
			return True
		return False

