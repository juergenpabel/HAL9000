from asyncio import Queue as asyncio_Queue
from logging import getLogger as logging_getLogger


class Frontend:
	LOG_LEVEL_TRACE = 5

	FRONTEND_RUNLEVEL_STARTING = 'starting'
	FRONTEND_RUNLEVEL_READY    = 'ready'
	FRONTEND_RUNLEVEL_RUNNING  = 'running'
	FRONTEND_RUNLEVEL_DEAD     = 'dead'

	FRONTEND_STATUS_UNKNOWN  = 'unknown'
	FRONTEND_STATUS_ONLINE   = 'online'
	FRONTEND_STATUS_OFFLINE  = 'offline'

	def __init__(self, name: str):
		self.name = name
		self.commands = asyncio_Queue()
		self.events = asyncio_Queue()
		self.config = {}
		self.tasks = {}
		self.runlevel = Frontend.FRONTEND_RUNLEVEL_STARTING
		self.status = Frontend.FRONTEND_STATUS_UNKNOWN


	async def configure(self, configuration) -> bool:
		return True


	async def start(self) -> None:
		self.runlevel = Frontend.FRONTEND_RUNLEVEL_RUNNING


	def __setattr__(self, name, new_value) -> None:
		old_value = None
		if hasattr(self, name) is True:
			old_value = getattr(self, name)
		super().__setattr__(name, new_value)
		if name in ['runlevel', 'status']:
			if old_value != new_value:
				logging_getLogger('uvicorn').debug(f"[frontend:{self.name}] {name} is now '{new_value}'")
				self.events.put_nowait({'topic': name, 'payload': new_value})

