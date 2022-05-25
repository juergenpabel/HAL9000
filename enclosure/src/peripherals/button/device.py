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
			self.button['status'] = list()
			for button in range(0, 4):
				self.button['status'].append(False)
			self.button['name'] = list()
			for button in range(0, 4):
				key = 'button.{}'.format(button)
				self.button['name'].append(configuration.get(str(self), key, fallback=key))
			self.driver = Driver('{}:{}'.format(configuration.get(str(self), 'driver'), device))
			self.driver.configure(configuration)


	def do_loop(self, callback_event = None) -> bool:
		if self.driver is not None:
			self.driver.do_loop()
			if callback_event is not None:
				peripheral, device = str(self).split(':')
				for number in range(0, 4):
					button_old = self.button['status'][number]
					button_new = self.calculate_button(self.driver.channel(number))
					if button_new is not None and button_old != button_new:
						self.button['status'][number] = button_new
						callback_event(peripheral, device, self.button['name'][number], int(button_new))
			return True
		return False


	def calculate_button(self, value: int) -> bool:
		if value < 64:
			return True
		if value > 192:
			return False
		return None

