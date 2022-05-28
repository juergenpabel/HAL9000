#!/usr/bin/python3


from configparser import ConfigParser

from hal9000.abstract import HAL9000_Abstract


class HAL9000_Driver(HAL9000_Abstract):

	def __init__(self, name: str) -> None:
		HAL9000_Abstract.__init__(self, name)

	# TODO: generic property generator for input pins like so:
	# self.driver = = MCP23017(..., [A0,A1,A2,A3,B4,B5,B6,B7])
	# ...in Driver class...
	# setattr(self, 'A0', property(getter,setter))
	# ...in Device class...
	# while self.driver.do_loop():
	#	input = getattr(self.driver, 'A0')
		
