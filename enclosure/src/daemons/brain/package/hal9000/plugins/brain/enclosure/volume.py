#!/usr/bin/python3

from configparser import ConfigParser
from datetime import datetime, timedelta
from numpy import cbrt
from alsaaudio import cards as alsa_cards, Mixer, VOLUME_UNITS_PERCENTAGE, VOLUME_UNITS_RAW, ALSAAudioError

from hal9000.brain.daemon import Daemon
from hal9000.plugins.brain.enclosure import EnclosureComponent


class Volume(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.alsamixer = None
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		EnclosureComponent.configure(self, configuration, section_name, cortex)
		if 'volume' not in cortex['enclosure']:
			cortex['enclosure']['volume'] = dict()
		self.config['volume-minimum'] = configuration.getint('enclosure:volume', 'volume-minimum', fallback=0)
		self.config['volume-maximum'] = configuration.getint('enclosure:volume', 'volume-maximum', fallback=100)
		self.config['volume-step']    = configuration.getint('enclosure:volume', 'volume-step',    fallback=5)
		for card in alsa_cards():
			alsa_section = "alsa:{}".format(card)
			if 'alsa-control' not in self.config or self.config['alsa-control'] is None:
				if configuration.has_section(alsa_section):
					self.config['alsa-control'] = configuration.get(alsa_section, 'control', fallback=None)
					self.config['alsa-cardindex'] = configuration.getint(alsa_section, 'cardindex', fallback=0)
					self.config['alsa-range-raw-minimum'] = configuration.getint(alsa_section, 'range-raw-minimum', fallback=None)
					self.config['alsa-range-raw-maximum'] = configuration.getint(alsa_section, 'range-raw-maximum', fallback=None)
		if 'alsa-control' not in self.config or self.config['alsa-control'] is None:
			self.daemon.logger.error("AUDIO: MISSING ALSA configuration => disabling volume control")
			self.daemon.logger.info ("AUDIO: configure 'alsa-control' (and optionally 'alsa-cardindex' if not 0) in section 'alsa:*'")
			if 'volume' in cortex['enclosure']:
				del cortex['enclosure']['volume']
		if 'volume' in cortex['enclosure']:
			try:
				self.alsamixer = Mixer(self.config['alsa-control'], cardindex=self.config['alsa-cardindex'])
				initial_volume = configuration.getint('enclosure:volume', 'initial-volume', fallback=None)
				if initial_volume is not None:
					initial_volume = min(initial_volume, self.config['volume-maximum'])
					initial_volume = max(initial_volume, self.config['volume-minimum'])
					cortex['enclosure']['volume']['level'] = initial_volume
					self.set_alsa_volume(initial_volume)
				else:
					cortex['enclosure']['volume']['level'] = self.alsamixer.getvolume(VOLUME_UNITS_PERCENTAGE)[0]
					cortex['enclosure']['volume']['level'] -= cortex['enclosure']['volume']['level'] % self.config['volume-step']
				if cortex['enclosure']['volume']['level'] > 0:
					cortex['enclosure']['volume']['mute'] = configuration.getboolean('enclosure:volume', 'initial-mute', fallback=False)
				else:
					cortex['enclosure']['volume']['mute'] = True
				if cortex['enclosure']['volume']['mute'] is True:
					self.set_alsa_volume(0)
			except ALSAAudioError as e:
				self.daemon.logger.error("alsaaudio.Mixer('{}',cardindex={}) raised '{}') => disabling volume control"
				                        .format(self.config['alsa-control'], self.config['alsa-cardindex'], e))
				del cortex['enclosure']['volume']


	def process(self, signal: dict, cortex: dict) -> None:
		EnclosureComponent.process(self, signal, cortex)
		if 'volume' not in cortex['enclosure']:
			return
		if 'gui/overlay' in self.daemon.timeouts:
			timeout, overlay = self.daemon.timeouts['gui/overlay']
			if overlay != 'volume':
				self.daemon.hide_gui_overlay(overlay)
				del self.daemon.timeouts['gui/overlay']
		if cortex['#activity']['audio'].module == "none":
			if 'volume' in signal:
				if self.alsamixer is None:
					self.daemon.show_gui_overlay('error', {"text": "NO SOUND DEVICE"}, 10)
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
						self.daemon.show_gui_overlay('volume', ({"level": str(cortex['enclosure']['volume']['level']), "mute": "false"}), 3)
				if 'mute' in signal['volume']:
					if signal['volume']['mute'] == "on":
						cortex['enclosure']['volume']['mute'] = True
						self.set_alsa_volume(0)
						self.daemon.show_gui_overlay('volume', ({"level": str(cortex['enclosure']['volume']['level']), "mute": "true"}), 0)
					if signal['volume']['mute'] == "off":
						cortex['enclosure']['volume']['mute'] = False
						self.set_alsa_volume(cortex['enclosure']['volume']['level'])
						self.daemon.show_gui_overlay('volume', ({"level": str(cortex['enclosure']['volume']['level']), "mute": "false"}), 3)
					self.daemon.logger.info('AUDIO: mute={}'.format(str(cortex['enclosure']['volume']['mute']).lower()))


	def set_alsa_volume(self, volume) -> None:
		if self.alsamixer is not None:
			mixer_raw_min, mixer_raw_max = self.alsamixer.getrange(units=VOLUME_UNITS_RAW)
			if self.config['alsa-range-raw-minimum'] is not None:
				if self.config['alsa-range-raw-minimum'] > mixer_raw_min:
					mixer_raw_min = self.config['alsa-range-raw-minimum']
			if self.config['alsa-range-raw-maximum'] is not None:
				if self.config['alsa-range-raw-maximum'] < mixer_raw_max:
					mixer_raw_max = self.config['alsa-range-raw-maximum']
			mixer_raw_vol = 0
			if volume >= self.config['volume-step']:
				mixer_raw_vol = int(cbrt(volume / 100.0) * (mixer_raw_max - mixer_raw_min) + mixer_raw_min)
			self.alsamixer.setvolume(mixer_raw_vol, units=VOLUME_UNITS_RAW)
			self.daemon.logger.info("AUDIO: alsa volume = {} (raw={} [{}-{}])".format(volume, mixer_raw_vol, mixer_raw_min, mixer_raw_max))

