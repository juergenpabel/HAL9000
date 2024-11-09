from os.path import dirname as os_path_dirname, \
                    abspath as os_path_abspath
from configparser import ConfigParser as configparser_ConfigParser
from json import load as json_load, \
                 loads as json_loads
from requests import get as requests_get

from hal9000.brain.plugin import HAL9000_Plugin, DataInvalid, CommitPhase
from hal9000.brain.plugins.enclosure import EnclosureComponent


class Control(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		super().__init__('trigger:enclosure:control', **kwargs)
		self.menu = None


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.config['menu:timeout'] = configuration.getint('enclosure:control', 'timeout', fallback=30)
		self.config['menu:loader'] = configuration.get('enclosure:control', 'loader', fallback='file')
		self.config['menu:loader-source'] = configuration.get('enclosure:control', self.config['menu:loader'], fallback=None)
		self.config['menu:processor'] = configuration.get('enclosure:control', 'processor', fallback='none')
		self.config['menu:processor-source'] = configuration.get('enclosure:control', self.config['menu:processor'], fallback=None)
		self.daemon.plugins['enclosure'].addSignalHandler(self.on_enclosure_signal)


	def menu_load(self, loader: str, loader_source: str, processor: str, processor_source: str) -> bool:
		if loader_source is None:
			self.daemon.logger.error(f"[enclosure:control] no source for loading the menu configured (missing key " \
			                         f"'{self.config['menu:loader']}' in section 'enclosure:control')")
			return False
		match loader:
			case 'file':
				try:
					if loader_source.startswith('/') is False and loader_source != self.config['menu:loader-source']:
						loader_source = f'{os_path_dirname(os_path_abspath(self.config["menu:loader-source"]))}/{loader_source}'
					with open(loader_source) as file:
						self.menu = json_load(file)
				except Exception as e:
					self.daemon.logger.error(f"[enclosure:control] error while loading file '{loader_source}': {e}")
					return False
			case 'url':
				try:
					json = requests_get(loader_source)
					self.menu = json_load(json)
				except Exception as e:
					self.daemon.logger.error(f"[enclosure:control] error while loading url '{loader_source}': {e}")
					return False
			case other:
				self.daemon.logger.error(f"[enclosure:control] invalid menu loader '{loader}' for '{loader_source}'")
				return False
		if 'id' not in self.menu or 'text' not in self.menu or 'items' not in self.menu or len(self.menu['items']) == 0:
			self.menu = None
			self.daemon.logger.error(f"[enclosure:control] invalid menu loaded from {loader}='{loader_source}'")
			return False
		match processor:
			case 'none' | None:
				pass
			case 'jinja2':
				pass # TODO
			case other:
				self.daemon.logger.error(f"[enclosure:control] invalid menu processor '{processor}' for '{self.menu['id']}'='{self.menu['text']}'")
				return False
		return True


	def menu_update_frontend(self, item_position) -> None:
		menu_id   = self.menu['id']
		menu_text = self.menu['text']
		item_id   = self.menu['items'][item_position]['id']
		item_text = self.menu['items'][item_position]['text']
		self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'menu', \
		                                                         'parameter': {'name': f'{menu_id}/{item_id}', 'title': menu_text, 'text': item_text}}}})
		self.daemon.create_scheduled_signal(self.config['menu:timeout'], 'frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}}, \
		                                    'scheduler://enclosure:control/menu:timeout')

	def menu_exit(self) -> None:
		self.menu = None
		self.daemon.remove_scheduled_signal('scheduler://enclosure:control/menu:timeout')
		self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})


	async def on_enclosure_signal(self, plugin: HAL9000_Plugin, signal: dict) -> None:
		if 'control' in signal:
			match self.daemon.plugins['frontend'].screen.split(':', 1).pop(0):
				case 'idle':
					if 'delta' in signal['control']:
						match self.menu_load(self.config['menu:loader'], self.config['menu:loader-source'], \
						                     self.config['menu:processor'], self.config['menu:processor-source']):
							case True:
								self.menu_update_frontend(0)
							case False:
								pass # TODO: error screen
				case 'menu':
					menu_id, item_id = self.daemon.plugins['frontend'].screen.split(':', 1).pop(1).split('/', 1)
					if menu_id != self.menu['id']:
						self.daemon.logger.error(f"[enclosure:control] BUG: shown menu '{menu_id}' is not loaded ('{self.menu['id']}')")
						self.menu_exit()
						return
					if len(list(filter(lambda item: item['id'] == item_id, self.menu['items']))) == 0:
						self.daemon.logger.error(f"[enclosure:control] BUG: shown menu item '{item_id}' is not in menu '{self.menu['id']}'")
						self.menu_exit()
						return
					if 'delta' in signal['control']:
						item = list(filter(lambda item: item['id'] == item_id, self.menu['items'])).pop(0)
						item_position = self.menu['items'].index(item)
						item_position += int(signal['control']['delta'])
						item_position %= len(self.menu['items'])
						self.menu_update_frontend(item_position)
					if 'select' in signal['control']:
						self.daemon.remove_scheduled_signal('scheduler://enclosure:control/menu:timeout')
						item = list(filter(lambda item: item['id'] == item_id, self.menu['items'])).pop(0)
						for action in item['actions'].copy():
							match action['handler']:
								case 'menu':
									menu_loader = action['data']['loader'] if 'loader' in action['data'] else 'file'
									menu_loader_source = action['data'][menu_loader] if menu_loader in action['data'] else None
									menu_processor = action['data']['processor'] if 'processor' in action['data'] else None
									menu_processor_source = action['data'][menu_processor] if menu_processor in action['data'] else None
									match self.menu_load(menu_loader, menu_loader_source, menu_processor, menu_processor_source):
										case True:
											self.menu_update_frontend(0) #TODO iterating after menu reload?
										case False: #TODO
											self.menu_exit()
											return
								case 'signal':
									plugin = action['data']['plugin']
									signal = self.daemon.substitute_vars(action['data']['signal'], \
									                                     {'ipv4': await self.daemon.get_system_ipv4()})
									self.daemon.queue_signal(plugin, signal)
								case other:
									self.daemon.logger.warning(f"[enclosure:control] invalid action handler '{action['handler']}' " \
									                           f"for menu item '{menu_id}/{item_id}', ignoring")
				case 'error':
					if 'select' in signal['control']: # TODO and not critical
						self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
				case 'qrcode':
					if 'select' in signal['control']:
						self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})

