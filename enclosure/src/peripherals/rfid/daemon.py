#!/usr/bin/python3

import sys
from smbus import SMBus
from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000
from device import Device as RFID


class Daemon(HAL9000):

	def __init__(self):
		HAL9000.__init__(self, 'rfid')
		self.rfid = RFID('smartcard')


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.rfid.configure(configuration)


	def do_loop(self) -> bool:
		self.rfid.do_loop(self.on_tag_enter, self.on_tag_leave)
		return True


	def on_tag_enter(self, uid: str) -> None:
		print("RFID: enter="+uid)
		if self.mqtt:
			self.mqtt.publish('{}/event'.format(self.config['mqtt-topic-prefix']), uid)


	def on_tag_leave(self, uid: str) -> None:
		print("RFID: leave="+uid)
		if self.mqtt:
			self.mqtt.publish('{}/event'.format(self.config['mqtt-topic-prefix']), '')



if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

