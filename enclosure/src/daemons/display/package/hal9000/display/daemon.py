#!/usr/bin/python3

import os
import sys
import base64

from configparser import ConfigParser

from hal9000.daemon import HAL9000_Daemon


class Daemon(HAL9000_Daemon):

	def __init__(self):
		HAL9000_Daemon.__init__(self, 'display')


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000_Daemon.configure(self, configuration)
		#TODO get env from config
		os.environ["BLINKA_FT232H"] = "1"
		Device = self.import_plugin('hal9000.display.device.displayio', 'Device')
		Driver = self.import_plugin('hal9000.display.driver.gc9a01', 'Driver')
		self.device = Device('waveshare-19192', Driver)
		self.device.configure(configuration)
		self.device.on_init()
		self.mqtt.subscribe('{}/enclosure/{}/splash/image'.format(self.config['mqtt-topic-base'], str(self)))
		self.mqtt.subscribe('{}/enclosure/{}/control'.format(self.config['mqtt-topic-base'], str(self)))
		self.mqtt.subscribe('{}/enclosure/{}/state/transition'.format(self.config['mqtt-topic-base'], str(self)))
		self.mqtt.subscribe('{}/enclosure/{}/splash/filename'.format(self.config['mqtt-topic-base'], str(self)))
		self.mqtt.subscribe('{}/enclosure/{}/overlay/volume'.format(self.config['mqtt-topic-base'], str(self)))
		


	def do_loop(self) -> bool:
		return self.device.do_loop(None)

	
	def on_mqtt(self, client, userdata, message):
		HAL9000_Daemon.on_mqtt(self, client, userdata, message)
		mqtt_base = self.config['mqtt-topic-base']
		if message.topic == '{}/enclosure/{}/control'.format(mqtt_base, str(self)):
			if message.payload.decode('utf-8') == "on":
				self.logger.debug("display => on")
				self.device.turn_display_on()
			if message.payload.decode('utf-8') == "off":
				self.logger.debug("display => off")
				self.device.turn_display_off()

			if message.payload.decode('utf-8') == "splash":
				self.logger.debug("splash")
				self.device.on_splash(None)
			if message.payload.decode('utf-8') == "wakeup":
				self.logger.debug("wakeup")
				self.device.on_wakeup()
			if message.payload.decode('utf-8') == "active":
				self.logger.debug("active")
				self.device.on_active()
			if message.payload.decode('utf-8') == "wait":
				self.device.on_wait()
			if message.payload.decode('utf-8') == "sleep":
				self.device.on_sleep()
		if message.topic == '{}/enclosure/{}/overlay/volume'.format(mqtt_base, str(self)):
			if message.payload.decode('utf-8') == "show":
				self.device.on_volume_show()
			if message.payload.decode('utf-8') == "hide":
				self.device.on_volume_hide()
		if message.topic == '{}/enclosure/{}/splash/image'.format(mqtt_base, str(self)):
			self.device.on_splash(message.payload.decode('utf-8'))


if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

