#!/usr/bin/python3

import os
import sys

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon as HAL9000


class Daemon(HAL9000):

	def __init__(self):
		HAL9000.__init__(self, 'display')


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		#TODO get env from config
		os.environ["BLINKA_FT232H"] = "1"
		Device = self.import_plugin('hal9000.display.device.displayio', 'Device')
		Driver = self.import_plugin('hal9000.display.driver.gc9a01', 'Driver')
		self.device = Device('waveshare-19192', Driver)
		self.device.configure(configuration)
#TODO		self.mqtt.subscribe('{}/{}/screen'.format(self.config['mqtt-topic-base'], str(self)))
#TODO		self.mqtt.subscribe('{}/{}/overlay/volume'.format(self.config['mqtt-topic-base'], str(self)))


	def do_loop(self) -> bool:
		return self.device.do_loop(None)

	
	def on_mqtt(self, client, userdata, message):
		HAL9000.on_mqtt(self, client, userdata, message)
		mqtt_base = self.config['mqtt-topic-base']
		if message.topic == '{}/{}/control'.format(mqtt_base, str(self)):
			if message.payload.decode('utf-8') == "init":
				print("init")
				self.device.on_init()
			if message.payload.decode('utf-8') == "wakeup":
				print("wakeup")
				self.device.on_wakeup()
			if message.payload.decode('utf-8') == "active":
				print("active")
				self.device.on_active()
			if message.payload.decode('utf-8') == "wait":
				self.device.on_wait()
			if message.payload.decode('utf-8') == "sleep":
				self.device.on_sleep()
		if message.topic == '{}/{}/overlay/volume'.format(mqtt_base, str(self)):
			if message.payload.decode('utf-8') == "show":
				self.device.on_volume_show()
			if message.payload.decode('utf-8') == "hide":
				self.device.on_volume_hide()


if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

