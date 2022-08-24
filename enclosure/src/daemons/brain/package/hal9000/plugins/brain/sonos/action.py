#!/usr/bin/python3

import platform
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain import HAL9000_Action
from configparser import ConfigParser
from soco import SoCo


class Action(HAL9000_Action):

	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'sonos', action_name, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		#print('TODO:action:sonos.config()')
		pass


	def process(self, signal: dict, cortex: dict) -> None:
		if 'rfid' in cortex['enclosure'] and cortex['enclosure']['rfid']['uid'] is not None:
			print('action:sonos.process({})'.format(signal))
			player = SoCo('192.168.3.30')
			player.volume += int(signal['volume']['delta'])

