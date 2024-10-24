from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.daemon import Brain
from hal9000.brain.plugins.enclosure import EnclosureComponent


class RFID(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		super().__init__('trigger:enclosure:rfid', **kwargs)
		self.daemon.plugins['enclosure'].addRemoteNames(['rfid'])


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.daemon.plugins['enclosure'].addNameCallback(self.on_enclosure_rfid_callback, 'rfid')
		self.daemon.plugins['enclosure'].addSignalHandler(self.on_enclosure_signal)
		self.daemon.plugins['enclosure'].rfid = None


	def on_enclosure_rfid_callback(self, plugin: HAL9000_Plugin_Data, key: str, old_rfid: str, new_rfid:str, phase: CommitPhase) -> bool:
		return True # TODO


	async def on_enclosure_signal(self, plugin: HAL9000_Plugin_Data, signal: dict) -> None:
		if 'rfid' in signal:
			pass #TODO

