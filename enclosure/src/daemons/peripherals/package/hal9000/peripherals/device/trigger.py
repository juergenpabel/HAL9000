#!/usr/bin/python3

import logging
from datetime import datetime, timedelta
from configparser import ConfigParser
from gpiozero import InputDevice

from hal9000.peripherals.device import HAL9000_Device
from hal9000.peripherals.driver import HAL9000_Driver


class Device(HAL9000_Device):

	def __init__(self, name: str, Driver: HAL9000_Driver):
		HAL9000_Device.__init__(self, 'trigger:{}'.format(name), Driver)
		self.config = dict()
		self.trigger = list()
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
				key = 'trigger.{}'.format(number)
				config = configuration.getlist(str(self), key, fallback=[key])
				self.config[key] = dict()
				self.config[key]['name'] = config[0].strip()
				self.config[key]['trigger'] = True
				self.config[key]['debounce'] = 0
				for option in config[1:]:
					option_key, option_value = option.split('=',1)
					option_key = option_key.strip().lower()
					option_value = option_value.strip().lower()
					if option_key == 'trigger':
						self.config[key]['trigger'] = bool(option_value=='true')
					if option_key == 'debounce':
						self.config[key]['debounce'] = float(option_value)
				self.trigger.append(dict())
				self.trigger[number]['debounce'] = None


	def do_loop(self, callback_event = None) -> bool:
		if self.driver is not None:
			self.driver.do_loop()
			if callback_event is not None:
				peripheral, device = str(self).split(':')
				driver_data = self.driver.switch_data
				for trigger_number in range(0, self.config['count']):
					key = 'trigger.{}'.format(trigger_number)
					if driver_data[trigger_number] == self.config[key]['trigger']:
						if self.debounce_trigger(trigger_number) is True:
							self.logger.debug('device:{} => trigger with label "{}" triggered'.format(self, self.config[key]['name']))
							callback_event(peripheral, device, self.config[key]['name'], 'trigger', True)
			return True
		return False


	def debounce_trigger(self, trigger_number):
		now = datetime.now()
		if self.trigger[trigger_number]['debounce'] is not None:
			if now < self.trigger[trigger_number]['debounce']:
				return False
			self.trigger[trigger_number]['debounce'] = None
		key = 'trigger.{}'.format(trigger_number)
		if self.config[key]['debounce'] > 0:
			self.trigger[trigger_number]['debounce'] = now + timedelta(milliseconds=self.config[key]['debounce'])
		return True

