#!/usr/bin/python3

import time
from smbus import SMBus
from configparser import ConfigParser
from gpiozero import InputDevice

from . import HAL9000_Driver as HAL9000


class Driver(HAL9000):

	IN            = 1
	OUT           = 0
	PULLUP        = 1
	HIGH          = 1
	LOW           = 0
	INVERT        = 1
	NONINVERT     = 0
	INT_ON_CHG    = 1
	INT_ON_DEFVAL = 0

	IODIRA   = (0x00, 0xFF, 'RW', 'IODIR')
	IPOLA    = (0x02, 0x00, 'RW', 'IPOL')
	GPINTENA = (0x04, 0x00, 'RW', 'GPINTEN')
	DEFVALA  = (0x06, 0x00, 'RW', 'DEFVAL')
	INTCONA  = (0x08, 0x00, 'RW', 'INTCON')
	IOCON    = (0x0A, 0x00, 'RW', 'IOCON')
	GPPUA    = (0x0C, 0x00, 'RW', 'GPPU')
	INTFA    = (0x0E, 0x00, 'RO', 'INTF')
	INTCAPA  = (0x10, 0x00, 'RO', 'INTCAP')
	GPIOA    = (0x12, 0x00, 'RW', 'GPIO')
	OLATA    = (0x14, 0x00, 'RW', 'OLAT')
	
	list_of_regs = [IODIRA, IPOLA, GPINTENA, DEFVALA, INTCONA, IOCON, 
	                GPPUA,  INTFA, INTCAPA,  GPIOA,   OLATA]

	
	def __init__(self, name: str, debug=False):
		HAL9000.__init__(self, name)
		self.config = dict()
		self.smbus = None
		self.device = None
		self.debug = False


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		#TODO: smbus singleton per bus
		self.config['i2c-bus'] = int(configuration.get(str(self), 'i2c-bus', fallback="1"), 16)
		self.config['i2c-address'] = int(configuration.get(str(self), 'i2c-address', fallback="0x20"), 16)
		self.smbus = SMBus(self.config['i2c-bus'])
		self.device = self.config['i2c-address']
		#self.reset()


	def do_loop(self, callback_rotary = None, callback_button = None) -> bool:
		#todo check and callbacks
		return True


	def check_valid_pin(self, pin):
		offset = -1
		if pin[0].upper() == 'A':
			offset = 0
		if pin[0].upper() == 'B':
			offset = 1
		if offset < 0:
			print("ERROR invalid pin bank")
			return -1
		if int(pin[1]) not in range(0,8):
			print("ERROR invalid pin number")
			return -1
		return offset


	# all parameters are POR values
	def setup(self, pin, direction, value=LOW, in_polarity=NONINVERT, in_pullup=False, int_en=False, int_on_change=False, int_defval=0):
		offset = self.check_valid_pin(pin)
		#check and set input direction
		read_direction = self.smbus.read_byte_data(self.device, self.IODIRA[0] + offset)
		if (direction == self.IN):
			direction_data = read_direction | (1 << int(pin[1]))
			#check and set polarity if input
			read_polarity = self.smbus.read_byte_data(self.device, self.IPOLA[0] + offset)
			if (in_polarity == self.INVERT):
				polarity_data = read_polarity | (1 << int(pin[1]))
			elif (in_polarity == self.NONINVERT):
				polarity_data = read_polarity & ( 0xFF - (1 << int(pin[1])) )
			else:
				print("ERROR in_polarity must be either 1 for invert or 0 for noninvert")
				return -1
			if (self.debug == True):
				print("Write address 0x{:02x} with data 0x{:02x}".format(self.IPOLA[0] + offset, polarity_data))
			self.smbus.write_byte_data(self.device, self.IPOLA[0] + offset, polarity_data)
			#set or clear pullup
			read_pullup = self.smbus.read_byte_data(self.device, self.GPPUA[0] + offset)
			if (in_pullup == True):
				pullup_data = read_pullup | (1 << int(pin[1]))
			else:
				pullup_data = read_pullup & ( 0xFF - (1 << int(pin[1])) )
			if (self.debug == True):
				print("Write address 0x{:02x} with data 0x{:02x}".format(self.GPPUA[0] + offset, pullup_data))
			self.smbus.write_byte_data(self.device, self.GPPUA[0] + offset, pullup_data)
			#set interupt enable and interrupt type
			read_int_en = self.smbus.read_byte_data(self.device, self.GPINTENA[0] + offset)
			if (int_en == True):
				int_en_data = read_int_en | (1 << int(pin[1]))
				read_int_on_change = self.smbus.read_byte_data(self.device, self.INTCONA[0] + offset)
				if (int_on_change == True):
					int_on_change_data = read_int_on_change | (1 << int(pin[1]))
				else:
					int_on_change_data = read_int_on_change & ( 0xFF - (1 << int(pin[1])) )
					#set defval if not interrupt on change type
					read_defval = self.smbus.read_byte_data(self.device, self.DEFVALA[0] + offset)
					if (int_defval == self.HIGH):
						defval_data = read_defval | (1 << int(pin[1]))
					elif (int_defval == self.LOW):
						defval_data = read_defval & ( 0xFF - (1 << int(pin[1])) )
					else:
						print("ERROR defval must be either 1 for high or 0 for low")
						return -1
					if (self.debug == True):
						print("Write address 0x{:02x} with data 0x{:02x}".format(self.DEFVALA[0] + offset, defval_data))
					self.smbus.write_byte_data(self.device, self.DEFVALA[0] + offset, defval_data)
				if (self.debug == True):
					print("Write address 0x{:02x} with data 0x{:02x}".format(self.INTCONA[0] + offset, int_on_change_data))
				self.smbus.write_byte_data(self.device, self.INTCONA[0] + offset, int_on_change_data)
			else:
				int_en_data = read_int_en & ( 0xFF - (1 << int(pin[1])) )
			if (self.debug == True):
				print("Write address 0x{:02x} with data 0x{:02x}".format(self.GPINTENA[0] + offset, int_en_data))
			self.smbus.write_byte_data(self.device, self.GPINTENA[0] + offset, int_en_data)
		#check and set output direction
		elif (direction == self.OUT):
			direction_data = read_direction & ( 0xFF - (1 << int(pin[1])) )
			#check and set output value
			read_out_val = self.smbus.read_byte_data(self.device, self.OLATA[0] + offset)
			if (value == self.HIGH):
				out_val_data = read_out_val | (1 << int(pin[1]))
			elif (value == self.LOW):
				out_val_data = read_out_val & ( 0xFF - (1 << int(pin[1])) )
			else:
				print("ERROR out_val must be either 1 for high or 0 for low")
				return -1
			if (self.debug == True):
				print("Write address 0x{:02x} with data 0x{:02x}".format(self.OLATA[0] + offset, out_val_data))
			self.smbus.write_byte_data(self.device, self.OLATA[0] + offset, out_val_data)
		else:
			print("ERROR direction must be either 1 for input or 0 for output")
			return -1
		if (self.debug == True):
			print("Write address 0x{:02x} with data 0x{:02x}".format(self.IODIRA[0] + offset, direction_data))
		self.smbus.write_byte_data(self.device, self.IODIRA[0] + offset, direction_data)

	
	def output(self, pin, value):
		offset = self.check_valid_pin(pin)
		#check direction
		read_direction = self.smbus.read_byte_data(self.device, self.IODIRA[0] + offset)
		if ((read_direction >> int(pin[1])) & self.IN):
			print("ERROR pin {:s} already configured as an input".format(pin))
			return -1
		read_out_val = self.smbus.read_byte_data(self.device, self.OLATA[0] + offset)
		if (value == self.HIGH):
			out_val_data = read_out_val | (1 << int(pin[1]))
		elif (value == self.LOW):
			out_val_data = read_out_val & ( 0xFF - (1 << int(pin[1])) )
		else:
			print("ERROR value must be either 1 for high or 0 for low")
			return -1
		if (self.debug == True):
			print("Write address 0x{:02x} with data 0x{:02x}".format(self.OLATA[0] + offset, out_val_data))
		self.smbus.write_byte_data(self.device, self.OLATA[0] + offset, out_val_data)


	# Be care when using this function with interrupts enabled as this function will clear the pin interrupt 
	def input(self, pin):
		offset = self.check_valid_pin(pin)
		#check direction
		read_direction = self.smbus.read_byte_data(self.device, self.IODIRA[0] + offset)
		if ((read_direction >> int(pin[1])) & self.IN != True):
			print("ERROR pin {:s} already configured as an output".format(pin))
			return -1
		read_gpio = self.smbus.read_byte_data(self.device, self.GPIOA[0] + offset)
		if ((read_gpio >> int(pin[1])) & self.HIGH):
			return self.HIGH
		else:
			return self.LOW


	def reset(self):
		for reg in self.list_of_regs:
			if reg[2] == 'RW':
				self.smbus.write_byte_data(self.device, reg[0] + 0, reg[1])
				self.smbus.write_byte_data(self.device, reg[0] + 1, reg[1])
				if self.debug:
					print("Write to {:s}A and {:s}B value 0x{:02x}".format(reg[3], reg[3], reg[1]))

