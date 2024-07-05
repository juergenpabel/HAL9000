import configparser
import json

from hal9000.brain.daemon import Daemon
from hal9000.brain.plugins.enclosure import EnclosureComponent


class Volume(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()


	def configure(self, configuration: configparser.ConfigParser, section_name: str) -> None:
		EnclosureComponent.configure(self, configuration, section_name)
		self.config['volume-step']    = configuration.getint('enclosure:volume', 'volume-step',    fallback=5)
		self.config['initial-mute']   = configuration.getboolean('enclosure:volume', 'initial-mute', fallback=False)
		self.config['initial-volume'] = configuration.getint(    'enclosure:volume', 'initial-volume', fallback=50)
		self.daemon.plugins['kalliope'].addNames(['volume', 'mute'])
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_status_callback, 'status')
		self.daemon.plugins['enclosure'].addSignalHandler(self.on_enclosure_signal)


	def on_kalliope_status_callback(self, plugin, name, old_value, new_value):
		if new_value == 'ready':
			plugin.volume = int(self.config['initial-volume'])
			plugin.mute = str(self.config['initial-mute']).lower()
		return True


	async def on_enclosure_signal(self, plugin, signal: dict) -> None:
		if 'volume' in signal:
			self.daemon.cancel_signal('frontend:gui/overlay#volume')
			if 'delta' in signal['volume']:
				if self.daemon.plugins['kalliope'].mute == 'false':
					delta = int(signal['volume']['delta']) * self.config['volume-step']
					volume = self.daemon.plugins['kalliope'].volume + delta
					volume = min(volume, 100)
					volume = max(volume, 0)
					self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'volume',
					                                                          'parameter': {'level': str(volume), 'mute': 'false'}}}})
					self.daemon.plugins['kalliope'].volume = volume
					self.daemon.schedule_signal(3, 'frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}}, 'frontend:gui/overlay#volume')

			if 'mute' in signal['volume']:
				mute = not(False if self.daemon.plugins['kalliope'].mute == 'false' else True)
				volume = self.daemon.plugins['kalliope'].volume
				self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'volume',
				                                                          'parameter': {'level': str(volume), 'mute': str(mute).lower()}}}})
				self.daemon.plugins['kalliope'].mute = str(mute).lower()
				if mute is False:
					self.daemon.schedule_signal(1, 'frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}}, 'frontend:gui/overlay#volume')

