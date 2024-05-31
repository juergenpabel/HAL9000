from asyncio import Queue as asyncio_Queue


class Frontend:

	def __init__(self):
		self.config = dict()
		self.commands = asyncio_Queue()
		self.events = asyncio_Queue()

