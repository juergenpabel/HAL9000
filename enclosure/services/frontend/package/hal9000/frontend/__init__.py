import asyncio
import configparser


class Frontend:

	def __init__(self):
		self.config = dict()
		self.commands = asyncio.Queue()
		self.events = asyncio.Queue()


	async def configure(self, filename) -> bool:
		if filename is not None:
			self.config = configparser.ConfigParser(delimiters='=',
			                                        converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
                                                                            'string': lambda string: string.strip('"').strip("'")},
								interpolation=None)
			self.config.read(filename)
		return True


