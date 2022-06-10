#!/usr/bin/python3

import datetime
import alsaaudio

from hal9000.brain import HAL9000_Action
from configparser import ConfigParser


class Action(HAL9000_Action):
	def __init__(self, action_name: str) -> None:
		HAL9000_Action.__init__(self, 'hal9000', 'self')
		self.config = dict()
		self.config['control'] = dict()
		self.config['volume'] = dict()
		self.config['rfid'] = dict()
		self.alsamixer = alsaaudio.Mixer('Speaker')


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		self.config['volume']['minimum'] = configuration.getint('settings', 'volume-minimum', fallback=0)
		self.config['volume']['maximum'] = configuration.getint('settings', 'volume-maximum', fallback=100)
		self.config['volume']['step'] = configuration.getint('settings', 'volume-step', fallback=10)
		default_volume = self.config['volume']['minimum'] + (self.config['volume']['maximum']-self.config['volume']['minimum'])/2
		self.config['volume']['initial-level'] = configuration.getint('settings', 'volume-level', fallback=int(default_volume))
		self.config['volume']['initial-mute'] = configuration.getboolean('settings', 'volume-mute', fallback=False)

		self.alsamixer.setvolume(self.config['volume']['initial-level'])
		#TODO:self.alsamixer.setmute(self.config['volume']['initial-mute'])


	def process(self, signal: dict, cortex: dict) -> dict:
		if 'daemon' not in signal:
			#TODO error
			return None
		daemon = signal['daemon']
		if 'volume' not in cortex:
			cortex['volume'] = dict()
			cortex['volume']['level'] = self.alsamixer.getvolume()[0]
			cortex['volume']['mute'] = False # TODO:self.alsamixer.getmute()

		if 'rfid' not in cortex['enclosure'] or cortex['enclosure']['rfid']['uid'] is None:
			if 'volume' in signal:
				if 'delta' in signal['volume']:
					delta = int(signal['volume']['delta']) * self.config['volume']['step']
					volume = cortex['volume']['level'] + delta
					if volume < self.config['volume']['minimum']:
						volume = self.config['volume']['minimum']
					if volume > self.config['volume']['maximum']:
						volume = self.config['volume']['maximum']
					self.alsamixer.setvolume(volume)
					cortex['volume']['level'] = self.alsamixer.getvolume()[0]
					if daemon is not None:
						daemon.show_display_overlay('volume')
						daemon.timeouts['overlay'] = datetime.datetime.now()+datetime.timedelta(seconds=3), 'volume'
						daemon.logger.info('volume={}'.format(cortex['volume']['level']))
				if 'mute' in signal['volume']:
					if int(signal['volume']['mute']) == 0: ## reminder: 0 is the button released event
						cortex['volume']['mute'] = not(cortex['volume']['mute'])
						#TODO:self.alsamixer.setmute(cortex['volume']['mute'])
						if daemon is not None:
							daemon.show_display_overlay('mute')
							daemon.timeouts['overlay'] = datetime.datetime.now()+datetime.timedelta(seconds=3), 'mute'
							daemon.logger.info('mute={}'.format(cortex['volume']['mute']))
		return cortex

