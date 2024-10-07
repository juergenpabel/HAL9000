from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.brain.plugin import HAL9000_Plugin, HAL9000_Plugin_Data, CommitPhase
from hal9000.brain.plugins.kalliope.action import Action as Action_Kalliope
from hal9000.brain.plugins.enclosure import EnclosureComponent


class Volume(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = {}


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		EnclosureComponent.configure(self, configuration, section_name)
		self.config['volume-step']    = configuration.getint('enclosure:volume', 'volume-step',    fallback=5)
		self.config['initial-mute']   = configuration.getboolean('enclosure:volume', 'initial-mute', fallback=False)
		self.config['initial-volume'] = configuration.getint('enclosure:volume', 'initial-volume', fallback=50)
		self.daemon.plugins['brain'].addNameCallback(self.on_brain_runlevel_callback, 'runlevel')
		self.daemon.plugins['kalliope'].addNameCallback(self.on_kalliope_runlevel_callback, 'runlevel')
		self.daemon.plugins['enclosure'].addSignalHandler(self.on_enclosure_signal)


	def on_brain_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			if new_runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING:
				if self.daemon.plugins['kalliope'].volume == HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
					self.daemon.queue_signal('kalliope', {'volume': {'level': self.config['initial-volume']}})
				if self.daemon.plugins['kalliope'].mute == HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
					self.daemon.queue_signal('kalliope', {'mute': self.config['initial-mute']})
		return True


	def on_kalliope_runlevel_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_runlevel: str, new_runlevel: str, phase: CommitPhase) -> bool:
		if phase == CommitPhase.COMMIT:
			if new_runlevel == HAL9000_Plugin.RUNLEVEL_RUNNING:
				if self.daemon.plugins['kalliope'].volume == HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
					self.daemon.queue_signal('kalliope', {'volume': {'level': self.config['initial-volume']}})
				if self.daemon.plugins['kalliope'].mute == HAL9000_Plugin_Data.STATUS_UNINITIALIZED:
					self.daemon.queue_signal('kalliope', {'mute': self.config['initial-mute']})
		return True


	async def on_enclosure_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'volume' in signal:
			self.daemon.remove_scheduled_signal('scheduler://enclosure:volume/gui/overlay:timeout')
			if 'delta' in signal['volume']:
				if self.daemon.plugins['kalliope'].mute == 'false':
					delta = int(signal['volume']['delta']) * self.config['volume-step']
					volume = int(self.daemon.plugins['kalliope'].volume) + delta
					volume = min(volume, 100)
					volume = max(volume, 0)
					self.daemon.plugins['kalliope'].volume = str(volume)
					self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'volume', 'parameter': {'level': volume, 'mute': False}}}})
					self.daemon.create_scheduled_signal(3, 'frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}}, 'scheduler://enclosure:volume/gui/overlay:timeout')
			if 'mute' in signal['volume']:
				mute = not(True if self.daemon.plugins['kalliope'].mute == 'true' else False)
				volume = int(self.daemon.plugins['kalliope'].volume)
				self.daemon.plugins['kalliope'].mute = str(mute).lower()
				self.daemon.queue_signal('frontend', {'gui': {'overlay': {'name': 'volume', 'parameter': {'level': volume, 'mute': mute}}}})
				if mute is False:
					self.daemon.create_scheduled_signal(1, 'frontend', {'gui': {'overlay': {'name': 'none', 'parameter': {}}}}, 'scheduler://enclosure:volume/gui/overlay:timeout')

