#!/usr/bin/python3

from configparser import ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.brain.plugins.enclosure import EnclosureComponent


class RFID(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		EnclosureComponent.configure(self, configuration, section_name)
		self.daemon.cortex['plugin']['enclosure'].addNames(['rfid_uid'])
		self.daemon.cortex['plugin']['enclosure'].addNameCallback(self.on_enclosure_rfid_callback, 'rfid_uid')
		self.daemon.cortex['plugin']['enclosure'].addSignalHandler(self.on_enclosure_signal)
		self.daemon.cortex['plugin']['enclosure'].rfid_uid = None


	def on_enclosure_rfid_callback(self, plugin, key, old_value, new_value):
		pass #TODO


	async def on_enclosure_signal(self, signal):
		if 'rfid' in signal:
			pass #TODO

