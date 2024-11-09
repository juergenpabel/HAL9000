from json import dumps as json_dumps
from configparser import ConfigParser as configparser_ConfigParser
from requests import get as requests_get, \
                     put as requests_put

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, RUNLEVEL, CommitPhase


class Action(HAL9000_Action):

	def __init__(self, action_instance: str, **kwargs) -> None:
		super().__init__('http', **kwargs)
		self.module.hidden = True
		self.runlevel = RUNLEVEL.RUNNING, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.daemon.plugins['http'].addSignalHandler(self.on_http_signal)


	async def on_http_signal(self, plugin: str, signal: dict) -> None:
		requests_method = requests_get
		if 'method' in signal:
			match signal['method'].upper():
				case 'GET':
					requests_method = requests_get
				case 'PUT':
					requests_method = requests_put
				case other:
					self.module.daemon.logger.error(f"[http] unexpected http method '{signal['method']}'")
					return
		if 'url' in signal:
			try:
				requests_method(signal['url'])
			except Exception as e:
				self.module.daemon.logger.error(f"[http] {str(e)}")

