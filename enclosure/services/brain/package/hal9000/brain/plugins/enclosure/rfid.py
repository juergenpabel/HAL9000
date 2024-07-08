from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.brain.plugins.enclosure import EnclosureComponent


class RFID(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		EnclosureComponent.configure(self, configuration, section_name)
		self.daemon.plugins['enclosure'].addNames(['rfid'])
		self.daemon.plugins['enclosure'].addNameCallback(self.on_enclosure_rfid_callback, 'rfid')
		self.daemon.plugins['enclosure'].addSignalHandler(self.on_enclosure_signal)
		self.daemon.plugins['enclosure'].rfid = None


	def on_enclosure_rfid_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_rfid, new_rfid) -> bool:
		pass #TODO
		return True


	async def on_enclosure_signal(self, plugin: HAL9000_Plugin_Status, signal: dict) -> None:
		if 'rfid' in signal:
			pass #TODO

