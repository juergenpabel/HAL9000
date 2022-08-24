#!/usr/bin/python3

from datetime import datetime, timedelta
from configparser import ConfigParser

from hal9000.brain.daemon import Daemon
from hal9000.plugins.brain.enclosure import EnclosureComponent


class Kalliope(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		EnclosureComponent.configure(self, configuration, section_name, cortex)


	def process(self, signal: dict, cortex: dict) -> None:
		EnclosureComponent.process(self, signal, cortex)
		if cortex['brain']['consciousness']['state'] == Daemon.CONSCIOUSNESS_AWAKE:
			state = signal['kalliope']['state']
			if state in Daemon.CONSCIOUSNESS_AWAKE_VALID:
				self.daemon.emit_consciousness(state)


