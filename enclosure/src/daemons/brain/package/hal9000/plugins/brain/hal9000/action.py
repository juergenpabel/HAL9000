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
		self.status = dict()
		self.alsamixer = alsaaudio.Mixer('Playback')


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		self.config['control']['position'] = 0
		self.config['volume']['minimum'] = configuration.getint('settings', 'volume-minimum', fallback=0)
		self.config['volume']['maximum'] = configuration.getint('settings', 'volume-maximum', fallback=100)
		self.config['volume']['step'] = configuration.getint('settings', 'volume-step', fallback=10)
		default_volume = self.config['volume']['minimum'] + (self.config['volume']['maximum']-self.config['volume']['minimum'])/2
		self.status['volume-level'] = configuration.getint('settings', 'volume-initial', fallback=default_volume)
		self.alsamixer.setvolume(self.status['volume-level'])
		self.status['volume-mute'] = False


	def process(self, synapse_data: dict, brain_data: dict) -> None:
		if brain_data['cortex']['enclosure-rfid'] is None:
			if 'volume' in brain_data:
				daemon = brain_data['daemon']
				if 'delta' in brain_data['volume']:
					delta = int(brain_data['volume']['delta']) * self.config['volume']['step']
					volume = self.status['volume-level'] + delta
					if volume < self.config['volume']['minimum']:
						volume = self.config['volume']['minimum']
					if volume > self.config['volume']['maximum']:
						volume = self.config['volume']['maximum']
					self.alsamixer.setvolume(volume)
					self.status['volume-level'] = self.alsamixer.getvolume()[0]
					if daemon is not None:
						daemon.show_display_overlay('volume')
						daemon.timeouts['overlay'] = datetime.datetime.now()+datetime.timedelta(seconds=3), 'volume'
						daemon.logger.info('volume={}'.format(self.status['volume-level']))
				if 'mute' in brain_data['volume']:
					if int(brain_data['volume']['mute']) == 0: ## reminder: 0 is the button released event
						self.status['volume-mute'] = not(self.status['volume-mute'])
						self.alsamixer.setmute(self.status['volume-mute'])
						if daemon is not None:
							daemon.show_display_overlay('mute')
							daemon.timeouts['overlay'] = datetime.datetime.now()+datetime.timedelta(seconds=3), 'mute'
							daemon.logger.info('mute={}'.format(self.status['volume-mute']))

