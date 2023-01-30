#!/usr/bin/python3

import logging
import requests
import base64
import json
import jsonpath_rw
import os
import os.path
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.daemon.arduino import HAL9000_Action
from configparser import ConfigParser


class Action(HAL9000_Action):

	BRICKIES_ACTIONS = {'enter': 'inserted', 'leave': 'removed'}
	BRICKIES_PARAMETERS = ['brickies-reader-service', 'brickies-reader-name', 'brickies-card-event', 'brickies-card-uid']


	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'brickies', action_name, **kwargs)
		self.config = dict()
		self.variables = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		self.config['hal9000-mqtt-server'] = configuration.getstring('mqtt', 'server', fallback='127.0.0.1')
		self.config['hal9000-mqtt-port'] = configuration.getint('mqtt', 'port', fallback=1883)
		self.config['base-url'] = configuration.getstring(section_name, 'brickies-server-url', fallback=None)
		self.config['spotify-image-directory'] = configuration.getstring(section_name, 'spotify-image-directory', fallback='/tmp')
		for parameter_name in Action.BRICKIES_PARAMETERS:
			parameter_value = configuration.getstring(section_name, parameter_name, fallback=None)
			if parameter_value is not None:
				self.variables[parameter_name] = parameter_value


	def process(self, signal: dict, cortex: dict) -> None:
		if 'rfid' not in signal:
			return
		data = {"signal": signal, "cortex": cortex, "result": {}} 
		for parameter_name in Action.BRICKIES_PARAMETERS:
			if parameter_name in self.variables:
				parameter_value = self.variables[parameter_name]
				if parameter_value.find(':') >= 2:
					parser, source, selector = parameter_value.split(':',2)
					if parser == 'dict':
						parameter_value = data[source][selector]
					if parser == 'jsonpath':
						data_json = data[source]
						matches = jsonpath_rw.parse(selector).find(data_json)
						if len(matches) == 1:
							parameter_value = matches[0].value
						elif len(matches) > 1:
							logging.getLogger(str(self)).debug("jsonpath selector '{}' yielded multiple results, using first one".format(selector))
							parameter_value = matches[0].value
						else:
							logging.getLogger(str(self)).debug("jsonpath selector '{}' yielded no result".format(selector))
							parameter_value = None
				if parameter_value is not None:
					data['result'][parameter_name] = str(parameter_value)
		if 'brickies-reader-service' in data['result'] and 'brickies-reader-name' in data['result'] and 'brickies-card-event' in data['result'] and 'brickies-card-uid' in data['result']:
			reader_service = data['result']['brickies-reader-service']
			reader_name = data['result']['brickies-reader-name']
			card_event = data['result']['brickies-card-event']
			card_uid = data['result']['brickies-card-uid']
			if card_event in Action.BRICKIES_ACTIONS:
				card_event = Action.BRICKIES_ACTIONS[card_event]
			response = requests.get('{}/database/rfid/{}'.format(self.config['base-url'], card_uid))
			if response.status_code == 200:
				filename_cover = None
				if card_event == 'inserted':
					filename_uid = "{}/{}.jpg".format(self.config['spotify-image-directory'], card_uid)
					if os.path.exists(filename_uid) is False:
						artist_id = None
						response = requests.get('{}/spotify/album/{}'.format(self.config['base-url'], card_uid))
						if response.status_code == 200:
							album = json.loads(response.content)
							artist_id = album['artists'][0]['id']
						else:
							logging.getLogger(str(self)).error("ERROR: GET '{}' returned unexpected status {}".format(url, response.status_code))
						if artist_id is None:
							response = requests.get('{}/spotify/artist/{}'.format(self.config['base-url'], card_uid))
							if response.status_code == 200:
								artist = json.loads(response.content)
								artist_id = artist['id']
						if artist_id is not None:
							filename_jpg = "{}/{}.jpg".format(self.config['spotify-image-directory'], artist_id)
							if os.path.exists(filename_jpg) is False:
								response = requests.get('{}/image/spotify-artist/{}'.format(self.config['base-url'], artist_id))
								if response.status_code == 200:
									with open(filename_jpg, 'wb') as file:
										file.write(response.content)
							if os.path.exists(filename_jpg):
								os.symlink(filename_jpg, filename_uid)
					filename_cover = filename_uid
					data['cortex']['enclosure']['rfid']['uid'] = card_uid
				if card_event == 'removed':
					filename_cover = ""
					data['cortex']['enclosure']['rfid']['uid'] = None
				if filename_cover is not None:
					self.daemon.video_gui_screen_show('splash', {'filename': filename_cover})

			requests.put('{}/reader/{}/{}/{}/{}'.format(self.config['base-url'], reader_service, reader_name, card_event, card_uid))
		return data['cortex']
 

