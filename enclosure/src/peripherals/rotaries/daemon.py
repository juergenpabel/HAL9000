#!/usr/bin/python3

import sys

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000
from device import Device as Rotary


class Daemon(HAL9000):

	def __init__(self):
		HAL9000.__init__(self, 'rotaries')
		self.rotary_volume = Rotary('volume')
		self.rotary_control = Rotary('control')


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.rotary_volume.configure(configuration)
		self.rotary_control.configure(configuration)


	def do_loop(self) -> bool:
		result = True
		result &= self.rotary_volume.do_loop(self.on_volume, self.on_mute)
		result &= self.rotary_control.do_loop(self.on_control, self.on_power)
		return result


	def on_volume(self, value: int):
		print("volume={}".format(value))


	def on_mute(self, value: int):
		print("mute={}".format(value))


	def on_control(self, value: int):
		print("control={}".format(value))


	def on_power(self, value: int):
		print("power={}".format(value))



if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

