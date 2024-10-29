from enum import StrEnum as enum_StrEnum
from asyncio import Queue as asyncio_Queue
from logging import getLogger as logging_getLogger


class RUNLEVEL(enum_StrEnum):
	STARTING = 'starting'
	SYNCING  = 'syncing'
	RUNNING  = 'running'
	DEAD     = 'dead'


class STATUS(enum_StrEnum):
	ONLINE   = 'online'
	OFFLINE  = 'offline'


class Frontend:
	LOG_LEVEL_TRACE = 5
	STATUS_UNKNOWN  = 'unknown'


	def __init__(self, name: str):
		self.name = name
		self.logger = logging_getLogger('uvicorn')
		self.commands = asyncio_Queue()
		self.events = asyncio_Queue()
		self.config = {}
		self.tasks = {}
		self.runlevel = RUNLEVEL.STARTING
		self.status = Frontend.STATUS_UNKNOWN


	async def configure(self, configuration) -> bool:
		self.runlevel = RUNLEVEL.SYNCING
		return True


	async def start(self) -> None:
		self.runlevel = RUNLEVEL.RUNNING


	def __setattr__(self, name, new_value) -> None:
		old_value = None
		if hasattr(self, name) is True:
			old_value = getattr(self, name)
		super().__setattr__(name, new_value)
		if name in ['runlevel', 'status']:
			if old_value != new_value:
				self.logger.debug(f"[frontend:{self.name}] {name} is now '{new_value}'")
				self.events.put_nowait({'topic': name, 'payload': new_value})

