from asyncio import Queue as asyncio_Queue
from configparser import ConfigParser as configparser_ConfigParser


class Frontend:

	def __init__(self):
		self.config = dict()
		self.commands = asyncio_Queue()
		self.events = asyncio_Queue()


	async def configure(self, filename) -> bool:
		if filename is not None:
			self.config = configparser_ConfigParser(delimiters='=',
			                                        converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
                                                                            'string': lambda string: string.strip('"').strip("'")},
								interpolation=None)
			self.config.read(filename)
		return True


