#!/usr/bin/python3

from datetime import datetime, timedelta
from configparser import ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.plugins.brain.enclosure import EnclosureComponent


class Control(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()
		self.config['menu'] = list()
		self.config['menu'].append("Kalliope: Trigger")
		self.config['menu'].append("Settings")
		self.config['menu'].append("Restart Arduino")
		self.config['menu'].append("Restart Linux")


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		EnclosureComponent.configure(self, configuration, section_name, cortex)
		if 'control' not in cortex['enclosure']:
			cortex['enclosure']['control'] = dict()
			cortex['enclosure']['control']['position'] = 0


	def process(self, signal: dict, cortex: dict) -> None:
		EnclosureComponent.process(self, signal, cortex)
		if 'overlay' in self.daemon.timeouts:
			timeout, overlay = self.daemon.timeouts['overlay']
			if overlay != 'message':
				del self.daemon.timeouts['overlay']
				self.daemon.hide_gui_overlay(overlay)
		if 'delta' in signal['control']:
			position = cortex['enclosure']['control']['position']
			position += int(signal['control']['delta'])
			position %= len(self.config['menu'])
			self.daemon.show_gui_overlay('message', {"text": self.config['menu'][position]})
			self.daemon.timeouts['overlay'] = datetime.now()+timedelta(seconds=10), 'message'
			cortex['enclosure']['control']['position']  = position
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
					self.daemon.timeouts['overlay'] = datetime.now()+timedelta(seconds=3), 'message'

