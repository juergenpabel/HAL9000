#!/usr/bin/python3

from hal9000.daemon import HAL9000_Daemon as HAL9000
from device import Device as RFID
from smbus import SMBus


class Daemon(HAL9000):

	def __init__(self):
		HAL9000.__init__(self, 'rfid')


	def configure(self, filename: str) -> None:
		HAL9000.configure(self, filename)
		self.rfid = RFID(SMBus(1), 0x28)
		if filename is None: # todo if mqtt active
			self.rfid.configure(None, None)
		else:
			self.rfid.configure(self.on_tag_enter, self.on_tag_leave)


	def do_loop(self) -> bool:
		self.rfid.do_loop()
		return True


	def on_tag_enter(self, uid: str) -> None:
		self.mqtt.publish('hal9000/rfid/event', uid)


	def on_tag_leave(self, uid: str) -> None:
		self.mqtt.publish('hal9000/rfid/event', '')



if __name__ == "__main__":
	daemon = Daemon()
	daemon.configure(None)
	daemon.loop()

