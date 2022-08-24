#!/usr/bin/python3

import time
import datetime
import alsaaudio
import numpy

from hal9000.brain import HAL9000_Action
from hal9000.brain.daemon import Daemon
from configparser import ConfigParser


class Action(HAL9000_Action):
	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'enclosure', 'self', **kwargs)
		self.daemon = kwargs.get('daemon', None)
		self.config = dict()
		self.config['control'] = dict()
		self.config['enclosure'] = dict()
		self.config['enclosure']['control'] = dict()
		self.config['enclosure']['control']['menu'] = list()
		self.config['enclosure']['control']['menu'].append("Kalliope: Trigger")
		self.config['enclosure']['control']['menu'].append("Settings")
		self.config['enclosure']['control']['menu'].append("Restart Arduino")
		self.config['enclosure']['control']['menu'].append("Restart Linux")
		self.config['enclosure']['volume'] = dict()
		self.config['enclosure']['rfid'] = dict()
		self.alsamixer = None


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		HAL9000_Action.configure(self, configuration, section_name, cortex)
		self.config['enclosure']['volume']['minimum'] = configuration.getint('enclosure:volume', 'volume-minimum', fallback=0)
		self.config['enclosure']['volume']['maximum'] = configuration.getint('enclosure:volume', 'volume-maximum', fallback=100)
		self.config['enclosure']['volume']['step']    = configuration.getint('enclosure:volume', 'volume-step',    fallback=5)
		if cortex is not None and 'enclosure' in cortex:
			if 'control' not in cortex['enclosure']:
				cortex['enclosure']['control'] = dict()
			cortex['enclosure']['control']['position'] = 0

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
					self.alsamixer = alsaaudio.Mixer(alsa_control, cardindex=alsa_cardindex)
				except alsaaudio.ALSAAudioError as e:
					self.daemon.logger.error("alsaaudio.Mixer('{}',cardindex={}) raised '{}') => disabling volume control"
						            .format(alsa_control, alsa_cardindex, e))
					if 'volume' in cortex['enclosure']:
						del cortex['enclosure']['volume']
			if 'volume' in cortex['enclosure']:
				initial_volume = configuration.getint('enclosure:volume', 'initial-volume', fallback=None)
				if initial_volume is not None:
					initial_volume = min(initial_volume, self.config['enclosure']['volume']['maximum'])
					initial_volume = max(initial_volume, self.config['enclosure']['volume']['minimum'])
					mixer_raw_min, mixer_raw_max = self.alsamixer.getrange(units=alsaaudio.VOLUME_UNITS_RAW)
					mixer_raw_vol = numpy.cbrt(initial_volume / 100.0) * (mixer_raw_max - mixer_raw_min) + mixer_raw_min
					self.alsamixer.setvolume(int(mixer_raw_vol), units=alsaaudio.VOLUME_UNITS_RAW)
					self.daemon.logger.info("ALSA:{} volume = {}".format(alsa_control, initial_volume))
				initial_mute = configuration.getboolean('enclosure:volume', 'initial-mute', fallback=None)
				if initial_mute is not None:
					self.alsamixer.setmute(1 if initial_mute is True else 0)
					cortex['enclosure']['volume']['mute'] = initial_mute
					self.daemon.logger.info("ALSA:{} mute = {}".format(alsa_control, initial_mute))
				cortex['enclosure']['volume']['level'] = max(100, self.alsamixer.getvolume(alsaaudio.VOLUME_UNITS_PERCENTAGE)[0])
				cortex['enclosure']['volume']['mute'] = False if self.alsamixer.getmute()[0] == 0 else True

	def process(self, signal: dict, cortex: dict) -> dict:
		if 'kalliope' in signal:
			if cortex['brain']['consciousness']['state'] == Daemon.CONSCIOUSNESS_AWAKE:
				state = signal['kalliope']['state']
				if state in Daemon.CONSCIOUSNESS_AWAKE_VALID:
					self.daemon.emit_consciousness(state)
		if 'control' in signal:
			if 'overlay' in self.daemon.timeouts:
				timeout, overlay = self.daemon.timeouts['overlay']
				if overlay != 'message':
					del self.daemon.timeouts['overlay']
					self.daemon.hide_gui_overlay(overlay)
			if 'delta' in signal['control']:
				cortex['enclosure']['control']['position'] += int(signal['control']['delta'])
				cortex['enclosure']['control']['position'] %= len(self.config['enclosure']['control']['menu'])
				self.daemon.show_gui_overlay('message', {"text": self.config['enclosure']['control']['menu'][cortex['enclosure']['control']['position']]})
				self.daemon.timeouts['overlay'] = datetime.datetime.now()+datetime.timedelta(seconds=10), 'message'
			if 'select' in signal['control']:
				if 'overlay' in self.daemon.timeouts:
					timeout, overlay = self.daemon.timeouts['overlay']
					if overlay == 'message':
						del self.daemon.timeouts['overlay']
						self.daemon.hide_gui_overlay('message')
					if cortex['enclosure']['control']['position'] == 0:
						self.daemon.mqtt.publish(self.daemon.config['mqtt-voice-assistant-trigger'], None)
					elif cortex['enclosure']['control']['position'] == 2:
						self.daemon.arduino_system_reset()
					else:
						self.daemon.show_gui_screen('idle', {})
						self.daemon.show_gui_overlay('message', {"text": "NOT IMPLEMENTED"})
						self.daemon.timeouts['overlay'] = datetime.datetime.now()+datetime.timedelta(seconds=3), 'message'
		if 'volume' in signal:
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
						delta = int(signal['volume']['delta']) * self.config['enclosure']['volume']['step']
						volume = cortex['enclosure']['volume']['level'] + delta
						if volume < self.config['enclosure']['volume']['minimum']:
							volume = self.config['enclosure']['volume']['minimum']
						if volume > self.config['enclosure']['volume']['maximum']:
							volume = self.config['enclosure']['volume']['maximum']
						cortex['enclosure']['volume']['level'] = volume
						raw_min, raw_max = self.alsamixer.getrange(units=alsaaudio.VOLUME_UNITS_RAW)
						mixer_raw = numpy.cbrt(volume / 100.0) * (raw_max - raw_min) + raw_min
						self.alsamixer.setvolume(int(mixer_raw), units=alsaaudio.VOLUME_UNITS_RAW)
						self.daemon.show_gui_overlay('volume', ({"level": str(cortex['enclosure']['volume']['level']), "mute": str(cortex['enclosure']['volume']['mute'])}))
						self.daemon.timeouts['overlay'] = datetime.datetime.now()+datetime.timedelta(seconds=3), 'volume'
						self.daemon.logger.info('volume={}'.format(cortex['enclosure']['volume']['level']))
				if 'mute' in signal['volume']:
					if signal['volume']['mute'] == "on":
						cortex['enclosure']['volume']['mute'] = True
					else:
						cortex['enclosure']['volume']['mute'] = False
					self.alsamixer.setmute(0 if cortex['enclosure']['volume']['mute'] is False else 1)
					if signal['volume']['mute'] == "on":
						self.daemon.show_gui_overlay('volume', ({"level": str(cortex['enclosure']['volume']['level']), "mute": str(cortex['enclosure']['volume']['mute'])}))
					else:
						self.daemon.hide_gui_overlay('volume')
					if 'overlay' in self.daemon.timeouts:
						del self.daemon.timeouts['overlay']
					self.daemon.logger.info('mute={}'.format(cortex['enclosure']['volume']['mute']))
		return cortex

