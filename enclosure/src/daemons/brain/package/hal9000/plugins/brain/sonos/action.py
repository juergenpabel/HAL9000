#!/usr/bin/python3

import soco
from paho.mqtt.publish import single as mqtt_publish_message

from hal9000.brain import HAL9000_Action
from configparser import ConfigParser


class Action(HAL9000_Action):

	def __init__(self, action_name: str, **kwargs) -> None:
		HAL9000_Action.__init__(self, 'sonos', action_name, **kwargs)
		self.sonos = None

	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		self.config['sonos-name'] = configuration.get(section_name, 'sonos-name', fallback=None)
		self.config['sonos-ip']   = configuration.get(section_name, 'sonos-ip',   fallback=None)
		self.config['volume-step'] = configuration.getint(section_name, 'volume-step', fallback=5)
		if self.config['sonos-ip'] is None and self.config['sonos-name'] is not None:
			self.sonos = soco.by_name(self.config['sonos-name'])
		if self.config['sonos-ip'] is not None:
			self.sonos = soco.SoCo(self.config['sonos-ip'])


	def process(self, signal: dict, cortex: dict) -> None:
		if self.sonos is None:
			return
		if 'sonos' in signal:
			if 'trigger' in signal['sonos']:
				cortex['brain']['activity']['enclosure']['audio'] = str(self)
				self.daemon.arduino_show_gui_overlay('message', {"text": "<SONOS>"})
			return
		if cortex['brain']['activity']['enclosure']['audio'] == str(self):
			if 'volume' in signal:
				if 'delta' in signal['volume']:
					delta = int(signal['volume']['delta'])
					delta *= self.config['volume-step']
					volume = self.sonos.set_relative_volume(delta)
				if 'mute' in signal['volume']:
					if signal['volume']['mute'] == "on":
						self.sonos.mute = True
					else:
						self.sonos.mute = False
			if 'control' in signal:
				if 'select' in signal['control']:
					cortex['brain']['activity']['enclosure']['audio'] = None
					self.daemon.arduino_hide_gui_overlay('message')

