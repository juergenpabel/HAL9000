#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.brain import HAL9000_Trigger
from hal9000.brain.daemon import Daemon


class Trigger(HAL9000_Trigger):

	def __init__(self, trigger_name: str) -> None:
		HAL9000_Trigger.__init__(self, 'hal9000', 'self')
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict = None) -> None:
		HAL9000_Trigger.configure(self, configuration, section_name)


	def callbacks(self) -> dict:
		result = dict()
		topics = list()
		if self.config['topic'] is not None:
			topics.append(self.config['topic'])
		result['mqtt'] = topics
		return result


	def handle(self, message) -> dict:
		matches = re.match(self.config['payload-regex'], message.payload.decode('utf-8'))
		if matches is not None:
			print('TODO:trigger:hal9000.handle({})'.format(matches))
			return matches.groupdict()
		return None

