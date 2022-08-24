#!/usr/bin/python3

from alsaaudio import Mixer, VOLUME_UNITS_PERCENTAGE, VOLUME_UNITS_RAW, ALSAAudioError
from numpy import cbrt
from datetime import datetime, timedelta
from configparser import ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.plugins.brain.enclosure import EnclosureComponent


class Volume(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		EnclosureComponent.configure(self, configuration, section_name, cortex)
		if 'volume' not in cortex['enclosure']:
			cortex['enclosure']['volume'] = dict()
		self.config['volume-minimum'] = configuration.getint('enclosure:volume', 'volume-minimum', fallback=0)
		self.config['volume-maximum'] = configuration.getint('enclosure:volume', 'volume-maximum', fallback=100)
		self.config['volume-step']    = configuration.getint('enclosure:volume', 'volume-step',    fallback=5)
		self.config['alsa-range-minimum'] = configuration.getint('enclosure:volume', 'alsa-range-minimum', fallback=None)
		self.config['alsa-range-maximum'] = configuration.getint('enclosure:volume', 'alsa-range-maximum', fallback=None)
		if 'volume' not in cortex['enclosure']:
			cortex['enclosure']['volume'] = dict()
		alsa_cardindex = configuration.getint('enclosure:volume', 'alsa-cardindex', fallback=0)
		alsa_control   = configuration.get('enclosure:volume', 'alsa-control', fallback=None)
		if alsa_control is None:
			self.daemon.logger.error("MISSING ALSA configuration => disabling volume control")
			self.daemon.logger.info ("configure 'alsa-control' (and optionally 'alsa-cardindex' if not 0) in section 'volume'")
			if 'volume' in cortex['enclosure']:
				del cortex['enclosure']['volume']
		if 'volume' in cortex['enclosure']:
			try:
				self.alsamixer = Mixer(alsa_control, cardindex=alsa_cardindex)
			except ALSAAudioError as e:
				self.daemon.logger.error("alsaaudio.Mixer('{}',cardindex={}) raised '{}') => disabling volume control"
						    .format(alsa_control, alsa_cardindex, e))
				if 'volume' in cortex['enclosure']:
					del cortex['enclosure']['volume']
		if 'volume' in cortex['enclosure']:
			initial_volume = configuration.getint('enclosure:volume', 'initial-volume', fallback=None)
			if initial_volume is not None:
				initial_volume = min(initial_volume, self.config['volume-maximum'])
				initial_volume = max(initial_volume, self.config['volume-minimum'])
				cortex['enclosure']['volume']['level'] = initial_volume
				self.set_alsa_volume(initial_volume)
			else:
				cortex['enclosure']['volume']['level'] = self.alsamixer.getvolume(VOLUME_UNITS_PERCENTAGE)[0]
				cortex['enclosure']['volume']['level'] -= cortex['enclosure']['volume']['level'] % self.config['volume-step']
			initial_mute = configuration.getboolean('enclosure:volume', 'initial-mute', fallback=None)
			if initial_mute is not None:
				cortex['enclosure']['volume']['mute'] = initial_mute
				if initial_mute is True:
					self.set_alsa_volume(0)
			else:
				cortex['enclosure']['volume']['mute'] = (cortex['enclosure']['volume']['level'] == 0)



	def process(self, signal: dict, cortex: dict) -> None:
		EnclosureComponent.process(self, signal, cortex)
		if 'overlay' in self.daemon.timeouts:
			timeout, overlay = self.daemon.timeouts['overlay']
			if overlay != 'volume':
				del self.daemon.timeouts['overlay']
				self.daemon.hide_gui_overlay(overlay)
		if 'rfid' not in cortex['enclosure'] or cortex['enclosure']['rfid']['uid'] is None:
			if self.alsamixer is None:
				self.daemon.show_gui_overlay('message', {"type": "ERROR", "text": "NO ALSA DEVICE"})
				return
			if 'delta' in signal['volume']:
				if cortex['enclosure']['volume']['mute'] is False:
					delta = int(signal['volume']['delta']) * self.config['volume-step']
					volume = cortex['enclosure']['volume']['level'] + delta
					if volume < self.config['volume-minimum']:
						volume = self.config['volume-minimum']
					if volume > self.config['volume-maximum']:
						volume = self.config['volume-maximum']
					cortex['enclosure']['volume']['level'] = volume
					self.set_alsa_volume(volume)
					self.daemon.show_gui_overlay('volume', ({"level": str(cortex['enclosure']['volume']['level']), "mute": str(cortex['enclosure']['volume']['mute'])}))
					self.daemon.timeouts['overlay'] = datetime.now()+timedelta(seconds=3), 'volume'
			if 'mute' in signal['volume']:
				if signal['volume']['mute'] == "on":
					cortex['enclosure']['volume']['mute'] = True
					self.set_alsa_volume(0)
				if signal['volume']['mute'] == "off":
					cortex['enclosure']['volume']['mute'] = False
					self.set_alsa_volume(cortex['enclosure']['volume']['level'])
				if cortex['enclosure']['volume']['mute'] is True:
					self.daemon.show_gui_overlay('volume', ({"level": str(cortex['enclosure']['volume']['level']), "mute": str(cortex['enclosure']['volume']['mute'])}))
				else:
					self.daemon.hide_gui_overlay('volume')
				if 'overlay' in self.daemon.timeouts:
					del self.daemon.timeouts['overlay']
				self.daemon.logger.info('mute={}'.format(cortex['enclosure']['volume']['mute']))


	def set_alsa_volume(self, volume) -> None:
		mixer_raw_min, mixer_raw_max = self.alsamixer.getrange(units=VOLUME_UNITS_RAW)
		if self.config['alsa-range-minimum'] is not None:
			if self.config['alsa-range-minimum'] > mixer_raw_min:
				mixer_raw_min = self.config['alsa-range-minimum']
		if self.config['alsa-range-maximum'] is not None:
			if self.config['alsa-range-maximum'] < mixer_raw_max:
				mixer_raw_max = self.config['alsa-range-maximum']
		mixer_raw_vol = 0
		if volume >= self.config['volume-step']:
			mixer_raw_vol = int(cbrt(volume / 100.0) * (mixer_raw_max - mixer_raw_min) + mixer_raw_min)
		self.alsamixer.setvolume(mixer_raw_vol, units=VOLUME_UNITS_RAW)
		self.daemon.logger.info("ALSA volume = {} (raw={} [{}-{}])".format(volume, mixer_raw_vol, mixer_raw_min, mixer_raw_max))

