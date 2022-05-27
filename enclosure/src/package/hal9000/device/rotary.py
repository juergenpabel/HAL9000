#!/usr/bin/python3


from configparser import ConfigParser
from gpiozero import InputDevice

from hal9000.device import HAL9000_Device as HAL9000


class Device(HAL9000):

	ROTARY_MODE_POSITION = "position"
	ROTARY_MODE_DIRECTION = "direction"
	ROTARY_MODES = [ ROTARY_MODE_POSITION, ROTARY_MODE_DIRECTION ]

	def __init__(self, name: str):
		HAL9000.__init__(self, 'rotary:{}'.format(name))
		self.config = dict()
		self.device = dict()
		self.device['encoder'] = dict()
		self.device['encoder']['data'] = 0x00
		self.device['encoder']['direction'] = 0
		self.device['irq'] = None
		self.driver = None


	def configure(self, configuration: ConfigParser):
		HAL9000.configure(self, configuration)
		peripheral, device = str(self).split(':')
		self.config['enabled'] = configuration.getboolean(str(self), 'enabled', fallback=True)
		if self.config['enabled']:
			event_data = configuration.get(str(self), 'event-data', fallback=Device.ROTARY_MODE_POSITION)
			if event_data == Device.ROTARY_MODE_POSITION:
				self.config['event-data'] = Device.ROTARY_MODE_POSITION
				self.device['position'] = configuration.getint(str(self), 'position-initial', fallback=0)
				self.config['position-min'] = configuration.getint(str(self), 'position-min', fallback=0)
				self.config['position-max'] = configuration.getint(str(self), 'position-max', fallback=100)
				self.config['position-step'] = configuration.getint(str(self), 'position-step', fallback=1)
			elif event_data == Device.ROTARY_MODE_DIRECTION:
				self.config['event-data'] = Device.ROTARY_MODE_DIRECTION
			else:
				#TODO error msg
				self.config['enabled'] = False
		if self.config['enabled']:
			Driver = self.load_driver(configuration.get(str(self), 'driver'))
			self.driver = Driver('{}:{}'.format(configuration.get(str(self), 'driver'), device))
			self.driver.configure(configuration)

			driver_irq_pin = configuration.getint(str(self), 'driver-irq-pin', fallback=0)
			if driver_irq_pin > 0:
				self.config['driver-irq-pin'] = driver_irq_pin
				self.device['irq'] = InputDevice(pin=driver_irq_pin, pull_up=True)


	def do_loop(self, callback_event = None) -> bool:
		if self.driver is not None:
			peripheral, device = str(self).split(':')
			if self.device['irq'] is None or self.device['irq'].value == 0:
				#TODO: reset irq on driver
				event_data = None
				rotary_data = self.driver.rotary_data
				rotary_direction = self.calculate_direction(rotary_data[0], rotary_data[1])
				if rotary_direction != 0:
					event_formatter = '{}'
					if self.config['event-data'] == Device.ROTARY_MODE_DIRECTION:
						event_data = rotary_direction
						event_formatter = '{0:+}'
					elif self.config['event-data'] == Device.ROTARY_MODE_POSITION:
						event_data = self.device['position'] + (rotary_direction * self.config['position-step'])
						if event_data < self.config['position-min']:
							event_data = self.config['position-min']
						if event_data > self.config['position-max']:
							event_data = self.config['position-max']
						if event_data != self.device['position']:
							self.device['position'] = event_data
					if callback_event is not None:
						callback_event(peripheral, device, self.config['event-data'], event_formatter.format(event_data))
			return True
		return False


	def calculate_direction(self, valA: int, valB: int) -> int:
		encoder_state_data = ((valA&0x01) << 4) + ((valB&0x01) << 0)
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

