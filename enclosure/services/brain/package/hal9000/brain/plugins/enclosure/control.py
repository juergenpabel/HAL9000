from os.path import basename as os_path_basename, \
                    dirname as os_path_dirname, \
                    abspath as os_path_abspath
from configparser import ConfigParser as configparser_ConfigParser
from json import load as json_load, \
                 loads as json_loads
from subprocess import run as subprocess_run
from requests import get as requests_get
from jinja2 import Environment as jinja2_Environment, \
                   FileSystemLoader as jinja2_FileSystemLoader, \
                   select_autoescape as jinja2_select_autoescape

from hal9000.brain.plugin import HAL9000_Plugin, DataInvalid, CommitPhase
from hal9000.brain.plugins.enclosure import EnclosureComponent


class Control(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		super().__init__('trigger:enclosure:control', **kwargs)
		self.menu = None


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.config['menu:timeout'] = configuration.getint('enclosure:control', 'timeout', fallback=30)
		self.config['menu:default-loader'] = configuration.get('enclosure:control', 'default-loader', fallback='file')
		self.config['menu:default-loader-source'] = configuration.get('enclosure:control', self.config['menu:default-loader'], fallback=None)
		self.config['menu:default-processor'] = configuration.get('enclosure:control', 'processor', fallback='none')
		self.config['menu:default-processor-source'] = configuration.get('enclosure:control', self.config['menu:default-processor'], fallback=None)
		self.daemon.plugins['enclosure'].addSignalHandler(self.on_enclosure_signal)


	def menu_load(self, id: str, loader: str = None, loader_source: str = None, processor: str = None, processor_source: str = None) -> bool:
		menu = {}
		if loader_source is None and self.config['menu:default-loader-source'] is None:
			self.daemon.logger.error(f"[enclosure:control] no loader-source provided for menu '{id}' and no default value configured (missing key " \
			                         f"'{self.config['menu:default-loader']}' in section 'enclosure:control')")
			return False
		if processor is not None or self.config['menu:default-processor'] != 'none':
			if processor_source is None and self.config['menu:default-processor-source'] is None:
				self.daemon.logger.error(f"[enclosure:control] no processor-source provided for menu '{id}' and no default value configured (missing key " \
				                         f"'{self.config['menu:default-processor']}' in section 'enclosure:control')")
			return False
		loader = loader if loader is not None else self.config['menu:default-loader']
		loader_source = loader_source.format(id=id) if loader_source is not None else self.config['menu:default-loader-source'].format(id=id) if self.config['menu:default-loader-source'] is not None else None
		processor = processor if processor is not None else self.config['menu:default-processor']
		processor_source = processor_source.format(id=id) if processor_source is not None else self.config['menu:default-processor-source'].format(id=id) if self.config['menu:default-processor-source'] is not None else None
		match loader:
			case 'file':
				try:
					with open(loader_source) as file:
						menu = json_load(file)
				except Exception as e:
					self.daemon.logger.error(f"[enclosure:control] error while loading file '{loader_source}': {e}")
					return False
			case 'url':
				try:
					response = requests_get(loader_source, timeout=5)
					if response.ok is True:
						menu = response.json()
				except Exception as e:
					self.daemon.logger.error(f"[enclosure:control] error while loading url '{loader_source}': {e}")
					return False
			case 'command':
				try:
					menu = subprocess_run(loader_source, check=True, capture_output=True, text=True, timeout=5).stdout
				except Exception as e:
					self.daemon.logger.error(f"[enclosure:control] error trying to execute command '{loader_source}': {e}")
					return False
			case other:
				self.daemon.logger.error(f"[enclosure:control] invalid menu loader '{loader}' for '{loader_source}'")
				return False
		match processor:
			case 'none' | None:
				self.menu = menu
			case 'jinja2':
				try:
					processor_source_dir = os_path_dirname(os_path_abspath(processor_source))
					jinja2_env = jinja2_Environment(loader=jinja2_FileSystemLoader(processor_source_dir), autoescape=jinja2_select_autoescape())
					jinja2_tmpl = jinja2_env.get_template(os_path_basename(processor_source))
					self.menu = json_loads(jinja2_tmpl.render(menu))
				except Exception as e:
					self.daemon.logger.error(f"[enclosure:control] exception in processor 'jinja2' while loading menu '{loader_source}': {e}")
			case other:
				self.daemon.logger.error(f"[enclosure:control] invalid menu processor '{processor}' for '{self.menu['id']}'='{self.menu['text']}'")
				return False
		if 'id' not in self.menu or 'text' not in self.menu or 'items' not in self.menu or len(self.menu['items']) == 0:
			self.daemon.logger.error(f"[enclosure:control] invalid menu loaded from {loader}='{loader_source.format(id=id)}'")
			self.menu_exit()
			return False
		for item_index, item in enumerate(self.menu['items'].copy()):
			if 'actions' not in item:
				self.daemon.logger.error(f"[enclosure:control] removing invalid menu item '{item['id']}' (missing 'actions') " \
			                         f"in menu '{id}' (loaded from {loader}='{loader_source.format(id=id)}')")
				self.menu['items'].remove(item)
		for item_index, item in enumerate(self.menu['items']):
			for action_index, action in enumerate(item['actions'].copy()):
				if 'handler' not in action or 'data' not in action:
					if item in self.menu['items']:
						self.daemon.logger.error(f"[enclosure:control] removing invalid menu item '{item['id']}' (invalid 'actions') " \
					                         f"in menu '{id}' (loaded from {loader}='{loader_source.format(id=id)}')")
						self.menu['items'].remove(item)
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
						match self.menu_load('main'):
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
						for action in item['actions']:
							match action['handler']:
								case 'menu':
									id = action['data']['id'] if 'id' in action['data'] else item['id']
									loader = action['data']['loader'] if 'loader' in action['data'] else None
									loader_source = action['data'][loader] if loader in action['data'] else None
									processor = action['data']['processor'] if 'processor' in action['data'] else None
									processor_source = action['data'][processor] if processor in action['data'] else None
									match self.menu_load(id, loader, loader_source, processor, processor_source):
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

