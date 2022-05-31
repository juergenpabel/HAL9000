#!/usr/bin/python3

import platform
from hal9000.brain import HAL9000_Trigger
from configparser import ConfigParser


class Trigger(HAL9000_Trigger):

	def __init__(self, trigger_name: str) -> None:
		HAL9000_Trigger.__init__(self, 'hal9000', platform.node())
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		pass


	def callbacks(self) -> dict:
		result = dict()
		topics = list()
		if self.config['topic'] is not None:
			topics.append(self.config['topic'])
		result['mqtt'] = topics
		return result


	def handle(self, message) -> dict:
		print('TODO:trigger:hal9000.handle() => {}'.format(message.topic))
		matches = re.match(self.config['payload-regex'], message.payload.decode('utf-8'))
		if matches is not None:
			return matches.groupdict()
		return None

