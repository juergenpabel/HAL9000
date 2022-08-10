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
		self.config['enclosure'] = dict()
		self.config['enclosure']['volume'] = dict()
		self.config['enclosure']['rfid'] = dict()
		self.alsamixer = alsaaudio.Mixer('Speaker')


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict = None) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		self.config['enclosure']['volume']['minimum'] = configuration.getint('settings', 'volume-minimum', fallback=0)
		self.config['enclosure']['volume']['maximum'] = configuration.getint('settings', 'volume-maximum', fallback=100)
		self.config['enclosure']['volume']['step'] = configuration.getint('settings', 'volume-step', fallback=10)
		default_volume = self.config['enclosure']['volume']['minimum'] + (self.config['enclosure']['volume']['maximum']-self.config['enclosure']['volume']['minimum'])/2
		self.config['enclosure']['volume']['initial-level'] = configuration.getint('settings', 'volume-level', fallback=int(default_volume))
		self.config['enclosure']['volume']['initial-mute'] = configuration.getboolean('settings', 'volume-mute', fallback=False)
		if cortex is not None:
			if 'volume' not in cortex['enclosure']:
				cortex['enclosure']['volume'] = dict()
				cortex['enclosure']['volume']['level'] = self.config['enclosure']['volume']['initial-level']
				cortex['enclosure']['volume']['mute'] = self.config['enclosure']['volume']['initial-mute']
		self.alsamixer.setvolume(self.config['enclosure']['volume']['initial-level'])
		#TODO:self.alsamixer.setmute(self.config['enclosure']['volume']['initial-mute'])


	def process(self, signal: dict, cortex: dict) -> dict:
		if 'daemon' not in signal:
			#TODO error
			return None
		daemon = signal['daemon']
		if 'rfid' not in cortex['enclosure'] or cortex['enclosure']['rfid']['uid'] is None:
			if 'volume' in signal:
				if 'delta' in signal['volume']:
					if cortex['enclosure']['volume']['mute'] is False:
						delta = int(signal['volume']['delta']) * self.config['enclosure']['volume']['step']
						volume = cortex['enclosure']['volume']['level'] + delta
						if volume < self.config['enclosure']['volume']['minimum']:
							volume = self.config['enclosure']['volume']['minimum']
						if volume > self.config['enclosure']['volume']['maximum']:
							volume = self.config['enclosure']['volume']['maximum']
						self.alsamixer.setvolume(volume)
						cortex['enclosure']['volume']['level'] = self.alsamixer.getvolume()[0]
						if daemon is not None:
							daemon.show_display_overlay('volume', ({"level": str(cortex['enclosure']['volume']['level']), "mute": str(cortex['enclosure']['volume']['mute'])}))
							daemon.timeouts['overlay'] = datetime.datetime.now()+datetime.timedelta(seconds=3), 'volume'
							daemon.logger.info('volume={}'.format(cortex['enclosure']['volume']['level']))
				if 'mute' in signal['volume']:
					if signal['volume']['mute'] == "on":
						cortex['enclosure']['volume']['mute'] = True
					else:
						cortex['enclosure']['volume']['mute'] = False
					#TODO:self.alsamixer.setmute(cortex['enclosure']['volume']['mute'])
					if daemon is not None:
						if signal['volume']['mute'] == "on":
							daemon.show_display_overlay('volume', ({"level": str(cortex['enclosure']['volume']['level']), "mute": str(cortex['enclosure']['volume']['mute'])}))
						else:
							daemon.hide_display_overlay('volume')
						if 'overlay' in daemon.timeouts:
							del daemon.timeouts['overlay']
						daemon.logger.info('mute={}'.format(cortex['enclosure']['volume']['mute']))
		return cortex

