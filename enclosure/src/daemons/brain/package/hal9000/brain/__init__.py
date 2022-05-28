#!/usr/bin/python3

import os
import sys
import re

from configparser import ConfigParser

from paho.mqtt.publish import single as mqtt_publish_message
from hal9000.daemon import HAL9000_Daemon as HAL9000


class Daemon(HAL9000):

	def __init__(self):
		HAL9000.__init__(self, 'brain')


	def configure(self, configuration: ConfigParser) -> None:
		HAL9000.configure(self, configuration)
		self.config['payload-regex'] = configuration.get('mqtt:rfid-enter', 'payload-regex').strip('"').strip("'")
		self.mqtt.subscribe("{}/enclosure/rfid/event".format(self.config['mqtt-topic-base']))


	def do_loop(self) -> bool:
		return True

	
	def on_mqtt(self, client, userdata, message):
		HAL9000.on_mqtt(self, client, userdata, message)
		mqtt_base = self.config['mqtt-topic-base']
		if message.topic == '{}/enclosure/rfid/event'.format(mqtt_base):
			payload = message.payload.decode('utf-8')
			data = re.search(self.config['payload-regex'], payload)
			if data is not None:
				reader_instance = data.group(1)
				card_uid = data.group(2)
				mqtt_publish_message('brickies/reader/hal9000/%s/event' % (reader_instance),
				    '{"reader":{"service":"hal9000","name":"%s"},'
				    ' "card":{"event":"%s","uid":"%s"}}' % (reader_instance, "removed", card_uid),
				    hostname="192.168.4.1", port=1883,
				    client_id="brickies_reader_hal9000-{}".format(reader_instance))



if __name__ == "__main__":
	daemon = Daemon()
	daemon.load(sys.argv[1])
	daemon.loop()

