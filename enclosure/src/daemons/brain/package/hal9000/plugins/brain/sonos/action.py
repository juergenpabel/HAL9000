#!/usr/bin/python3

import platform
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain import HAL9000_Action
from configparser import ConfigParser


class Action(HAL9000_Action):

	def __init__(self, action_name: str) -> None:
		HAL9000_Action.__init__(self, 'sonos', action_name)


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		print('TODO:action:sonos.config()')


	def process(self, synapse_data: dict, brain_data: dict) -> None:
		if brain_data['cortex']['enclosure-rfid'] is not None:
			print('action:sonos.process({})'.format(synapse_data))
 
 

