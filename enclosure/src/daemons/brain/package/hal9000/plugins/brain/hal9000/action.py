#!/usr/bin/python3

import platform
from hal9000.abstract.plugin import HAL9000_Action as HAL9000
from configparser import ConfigParser


class Action(HAL9000):
	def __init__(self, action_name: str) -> None:
		HAL9000.__init__(self, 'hal9000', platform.node())
		self.config = dict()
		self.config['control'] = dict()
		self.config['volume'] = dict()
		self.config['rfid'] = dict()
		self.status = dict()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		print('TODO:action:hal9000.config()')
		print(section_name)
		self.config['control']['position'] = 0
		self.config['volume']['minimum'] = configuration.getint('settings', 'volume-minimum', fallback=0)
		self.config['volume']['maximum'] = configuration.getint('settings', 'volume-maximum', fallback=100)
		self.config['volume']['step'] = configuration.getint('settings', 'volume-step', fallback=10)

		default_volume = self.config['volume']['minimum'] + (self.config['volume']['maximum']-self.config['volume']['minimum'])/2
		self.status['volume-level'] = configuration.getint('settings', 'volume-initial', fallback=default_volume)
		self.status['volume-mute'] = False
		print(self.config)


	def process(self, synapse_data: dict, brain_data: dict) -> None:
		if 'volume' in brain_data:
			delta = int(brain_data['volume']) * self.config['volume']['step']
			volume = self.status['volume-level'] + delta
			if volume < self.config['volume']['minimum']:
				volume = self.config['volume']['minimum']
			if volume > self.config['volume']['maximum']:
				volume = self.config['volume']['maximum']
			self.status['volume-mute'] = False
			self.status['volume-level'] = volume
			print('volume={}'.format(volume))
		if 'mute' in brain_data:
			print(brain_data['mute'])
			if int(brain_data['mute']) == 0:
				self.status['volume-mute'] = not(self.status['volume-mute'])
			print('mute={}'.format(self.status['volume-mute']))

