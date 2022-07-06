#!/usr/bin/python3

import logging
from datetime import datetime, timedelta
from configparser import ConfigParser
from gpiozero import InputDevice

from hal9000.peripherals.device import HAL9000_Device
from hal9000.peripherals.driver import HAL9000_Driver


class Device(HAL9000_Device):

	def __init__(self, name: str, Driver: HAL9000_Driver):
		HAL9000_Device.__init__(self, 'switch:{}'.format(name), Driver)
		self.config = dict()
		self.switch = list()
		self.driver = None
		self.logger = logging.getLogger()


	def configure(self, configuration: ConfigParser, section_name: str = None):
		HAL9000_Device.configure(self, configuration, section_name)
		peripheral, device = str(self).split(':')
		self.config['enabled'] = configuration.getboolean(str(self), 'enabled', fallback=True)
		self.config['count'] = configuration.getint(str(self), 'count', fallback=1)
		if self.config['enabled']:
			self.driver = self.Driver('{}:{}'.format(configuration.getstring(str(self), 'driver'), device))
			self.driver.configure(configuration, section_name)

			for number in range(0, self.config['count']):
				key = 'switch.{}'.format(number)
				config = configuration.getlist(str(self), key, fallback=[key])
				self.config[key] = dict()
				self.config[key]['name'] = config[0].strip()
				self.config[key]['invert'] = False
				self.config[key]['debounce'] = 0
				for option in config[1:]:
					option_key, option_value = option.split('=',1)
					option_key = option_key.strip().lower()
					option_value = option_value.strip().lower()
					if option_key == 'invert':
						self.config[key]['invert'] = bool(option_value=='true')
					if option_key == 'debounce':
						self.config[key]['debounce'] = float(option_value)
				self.switch.append(dict())
				self.switch[number]['status'] = False
				self.switch[number]['debounce'] = None


	def do_loop(self, callback_event = None) -> bool:
		if self.driver is not None:
			self.driver.do_loop()
			if callback_event is not None:
				peripheral, device = str(self).split(':')
				driver_data = self.driver.switch_data
				for switch_number in range(0, self.config['count']):
					switch_old = self.switch[switch_number]['status']
					switch_new = self.calculate_status(switch_number, driver_data[switch_number])
					if switch_new is not None and switch_old != switch_new:
						key = 'switch.{}'.format(switch_number)
						self.switch[switch_number]['status'] = switch_new
						self.logger.debug('device:{} => switch with label "{}" changed to status={}'.format(self, self.config[key]['name'], switch_new))
						callback_event(peripheral, device, self.config[key]['name'], 'status', int(switch_new))
			return True
		return False


	def calculate_status(self, switch_number, switch_value):
		now = datetime.now()
		if self.switch[switch_number]['debounce'] is not None:
			if now < self.switch[switch_number]['debounce']:
				return None
		key = 'switch.{}'.format(switch_number)
		invert_value = self.config[key]['invert']
		switch_value = bool(invert_value != switch_value)
		if self.switch[switch_number]['debounce'] is None:
			if self.config[key]['debounce'] > 0:
				if switch_value != self.switch[switch_number]['status']:
					self.logger.debug("device:{} => debouncing switch '{}' for {} milliseconds...".format(self, self.config[key]['name'], self.config[key]['debounce']))
					self.switch[switch_number]['debounce'] = now + timedelta(milliseconds=self.config[key]['debounce'])
					return None
		self.switch[switch_number]['debounce'] = None
		return switch_value

