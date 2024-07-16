from asyncio import Queue as asyncio_Queue


class Frontend:
	FRONTEND_RUNLEVEL_STARTING = 'starting'
	FRONTEND_RUNLEVEL_READY    = 'ready'
	FRONTEND_RUNLEVEL_RUNNING  = 'running'

	FRONTEND_STATUS_UNKNOWN  = 'unknown'
	FRONTEND_STATUS_ONLINE   = 'online'
	FRONTEND_STATUS_OFFLINE  = 'offline'

	def __init__(self):
		self.runlevel = Frontend.FRONTEND_RUNLEVEL_STARTING
		self.status = Frontend.FRONTEND_STATUS_UNKNOWN
		self.commands = asyncio_Queue()
		self.events = asyncio_Queue()
		self.config = {}


	async def configure(self, configuration) -> bool:
		return True


	async def start(self) -> None:
		self.runlevel = Frontend.FRONTEND_RUNLEVEL_READY

