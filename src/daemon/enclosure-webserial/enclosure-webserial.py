#!/usr/bin/python3

import sys
import time
import json
import asyncio

from configparser import ConfigParser

from hal9000.daemon.abstract import HAL9000_Daemon
from hal9000.daemon.abstract import HAL9000_Plugin

from hal9000.daemon.enclosure.webserial import Agent
from hal9000.daemon.enclosure.webserial import Webserial


class EnclosureDaemon(HAL9000_Daemon):

	def __init__(self) -> None:
		super().__init__('enclosure-daemon')
		self.webserial = Webserial()
		self.agent = Agent()


	def configure(self, configuration: ConfigParser) -> None:
		super().configure(configuration)
		self.webserial.configure(configuration)
		self.agent.configure(configuration)


	async def loop(self) -> None:
		if self.uwsgi is not None:
			self.uwsgi.accepting()
		await asyncio.gather(self.webserial.loop(self.agent), self.agent.loop(self.webserial))


if __name__ == '__main__':
	try:
		daemon = EnclosureDaemon()
		daemon.load(sys.argv[1])
		asyncio.run(daemon.loop())
	except BaseException as e:
		print(f"{type(e)}({str(e)})")
		time.sleep(1)
		sys.exit(-1)

