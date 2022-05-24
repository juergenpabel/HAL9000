#!/usr/bin/python3


from configparser import ConfigParser
from gpiozero import InputDevice

from hal9000.device import HAL9000_Device as HAL9000

from hal9000.driver.pcf8591 import PCF8591 as Driver


class Device(HAL9000):

	def __init__(self, name: str):
		HAL9000.__init__(self, 'button:{}'.format(name))
		self.button = dict()


	def configure(self, configuration: ConfigParser):
		HAL9000.configure(self, configuration)
		peripheral, device = str(self).split(':')
		self.button['enabled'] = configuration.getboolean(str(self), 'button-enabled', fallback=True)
		if self.button['enabled']:
			self.button['status'] = [ False, False, False, False ] # list size is len(pins-sig)

		self.driver = Driver('{}:{}'.format(configuration.get(str(self), 'driver'), device))
		self.driver.configure(configuration)
#TODO		if self.button['enabled']:
#TODO			for pin in self.button['pins-sig']:
#TODO				#TODO:self.driver.setup(pin, Driver.IN, Driver.HIGH, Driver.NONINVERT, True, True, True)
#TODO			for pin in self.button['pins-gnd']:
#TODO				#TODO:self.driver.setup(pin, Driver.OUT, Driver.LOW)


	def do_loop(self, callback_event = None) -> bool:
		peripheral, device = str(self).split(':')
#TODO		if self.button['enabled']:
#TODO			for pin in self.button['pins-sig']:
#TODO				value = self.driver.input(pin)
#TODO				button_status = self.calculate_button(value)
#TODO				if button_status != self.button['status']:
#TODO					self.button['status'] = button_status
#TODO					if callback_event is not None:
#TODO						callback_event(peripheral, device, 'button', str(int(button_status)))
		return True


	def calculate_button(self, value: float) -> bool:
		#TODO
		return value

