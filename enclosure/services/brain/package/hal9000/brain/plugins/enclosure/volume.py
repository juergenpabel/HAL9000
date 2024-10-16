from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import Brain
from hal9000.brain.plugin import HAL9000_Plugin, HAL9000_Plugin_Data, CommitPhase
from hal9000.brain.plugins.kalliope.action import Action as Action_Kalliope
from hal9000.brain.plugins.enclosure import EnclosureComponent


class Volume(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, 'trigger:enclosure:volume', **kwargs)
		self.config = {}


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		EnclosureComponent.configure(self, configuration, section_name)
		self.config['volume-step']    = configuration.getint('enclosure:volume', 'volume-step',    fallback=5)
		self.daemon.plugins['enclosure'].addSignalHandler(self.on_enclosure_signal)


	async def on_enclosure_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'volume' in signal:
			self.daemon.remove_scheduled_signal('scheduler://enclosure:volume/gui/overlay:timeout')
			if 'delta' in signal['volume']:
				if self.daemon.plugins['kalliope'].mute == 'false':
					delta = int(signal['volume']['delta']) * self.config['volume-step']
					volume = int(self.daemon.plugins['kalliope'].volume) + delta
					volume = min(volume, 100)
					volume = max(volume, 0)
					self.daemon.queue_signal('kalliope', {'volume': {'level': volume}})
					self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'volume', 'parameter': {'level': volume, 'mute': False}}}})
					self.daemon.create_scheduled_signal(3, 'frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}}, 'scheduler://enclosure:volume/gui/overlay:timeout')
			if 'mute' in signal['volume']:
				mute = not(True if self.daemon.plugins['kalliope'].mute == 'true' else False)
				volume = int(self.daemon.plugins['kalliope'].volume)
				self.daemon.queue_signal('kalliope', {'volume': {'mute': mute}})
				self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'volume', 'parameter': {'level': volume, 'mute': mute}}}})
				if mute is False:
					self.daemon.create_scheduled_signal(1, 'frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}}, 'scheduler://enclosure:volume/gui/overlay:timeout')

