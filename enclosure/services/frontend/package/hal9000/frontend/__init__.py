from asyncio import Queue as asyncio_Queue


class Frontend:
	FRONTEND_STATUS_STARTING = 'starting'
	FRONTEND_STATUS_READY    = 'ready'
	FRONTEND_STATUS_ONLINE   = 'online'
	FRONTEND_STATUS_OFFLINE  = 'offline'

	def __init__(self):
		self.status = Frontend.FRONTEND_STATUS_STARTING
		self.commands = asyncio_Queue()
		self.events = asyncio_Queue()
		self.config = {}


	async def configure(self, configuration) -> bool:
		return True


	async def start(self) -> None:
		self.status = Frontend.FRONTEND_STATUS_READY

