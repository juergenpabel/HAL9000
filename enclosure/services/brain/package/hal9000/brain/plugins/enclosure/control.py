from json import loads as json_loads
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Plugin_Status
from hal9000.brain.plugins.enclosure import EnclosureComponent


class Control(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config['handlers'] = {}
		self.config['menu'] = {}
		self.config['menu']['menu-main'] = {}
		self.config['menu']['menu-main']['title'] = ''
		self.config['menu']['menu-main']['items'] = []
		self.daemon.plugins['frontend'].addNames(['menu_item', 'menu_name'])


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		EnclosureComponent.configure(self, configuration, section_name)
		self.config['menu']['timeout'] = configuration.getint('enclosure:control', 'timeout', fallback=15)
		menu_files = configuration.getlist('enclosure:control', 'menu-files', fallback=[])
		item_files = configuration.getlist('enclosure:control', 'item-files', fallback=[])
		files = [file for file in menu_files+item_files if file is not None]
		if len(files) > 0:
			menu_config = configparser_ConfigParser()
			menu_config.read(files)
			self.configure_menu(menu_config, 'menu-main')
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.plugins['enclosure'].addSignalHandler(self.on_enclosure_signal)


	def configure_menu(self, menu_config: configparser_ConfigParser, menu_self: str) -> None:
		self.config['menu'][menu_self]['title'] = menu_config.get(menu_self, 'title', fallback='')
		for menu_entry in menu_config.options(menu_self):
			if menu_entry.startswith('item-'):
				plugin = menu_config.get(menu_entry, 'plugin', fallback=None)
				signal = menu_config.get(menu_entry, 'signal', fallback=None)
				if plugin not in self.daemon.plugins:
					self.daemon.logger.error(f"[enclosure:control] unknown plugin configured for menu entry '{menu_entry}': '{plugin}'")
					continue
				try:
					signal = json_loads(signal)
				except Exception as e:
					self.daemon.logger.error(f"[enclosure:control] invalid signal configuration for menu entry '{menu_entry}': '{signal}'")
					continue
				self.config['menu'][menu_self]['items'].append({'item': menu_entry, 'text': menu_config.get(menu_self, menu_entry)})
				self.config['handlers'][menu_entry] = {}
				self.config['handlers'][menu_entry]['plugin'] = plugin
				self.config['handlers'][menu_entry]['signal'] = signal
			if menu_entry.startswith('menu-'):
				self.config['menu'][menu_self]['items'].append({'item': menu_entry, 'text': menu_config.get(menu_self, menu_entry)})
				if menu_entry not in self.config['menu']:
					self.config['menu'][menu_entry] = {}
					self.config['menu'][menu_entry]['items'] = []
					self.configure_menu(menu_config, menu_entry)


	def on_frontend_screen_callback(self, plugin: HAL9000_Plugin_Status, key: str, old_screen: str, new_screen: str) -> bool:
		if old_screen == 'menu':
			self.daemon.plugins['frontend'].menu_name = None
			self.daemon.plugins['frontend'].menu_item = None
		return True


	async def on_enclosure_signal(self, plugin: HAL9000_Plugin_Status, signal: dict) -> None:
		if 'control' in signal:
			match self.daemon.plugins['frontend'].screen:
				case 'none':
					pass
				case 'idle':
					if 'delta' in signal['control']:
						menu_name = 'menu-main'
						menu_item = self.config['menu']['menu-main']['items'][0]['item']
						menu_title = self.config['menu'][menu_name]['title']
						menu_text  = self.config['menu'][menu_name]['items'][0]['text']
						self.daemon.plugins['frontend'].screen = 'menu'
						self.daemon.plugins['frontend'].menu_name = menu_name
						self.daemon.plugins['frontend'].menu_item = menu_item
						self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'menu',
						                                                         'parameter': {'title': menu_title,
						                                                                       'text': menu_text}}}})
				case 'hal9000':
					pass
				case 'error':
					if 'select' in signal['control']:
						self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
				case 'qrcode':
					if 'select' in signal['control']:
						self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
				case 'menu':
					menu_name = self.daemon.plugins['frontend'].menu_name
					menu_item = self.daemon.plugins['frontend'].menu_item
					if 'delta' in signal['control']:
						self.daemon.schedule_signal(self.config['menu']['timeout'],
						                            'frontend',
						                            {'gui': {'screen': {'name': 'idle', 'parameter': {}}}},
						                            'menu:timeout')
						position = 0
						for item in self.config['menu'][menu_name]['items']:
							if item['item'] == menu_item:
								position = self.config['menu'][menu_name]['items'].index(item)
						position += int(signal['control']['delta'])
						position %= len(self.config['menu'][menu_name]['items'])
						menu_title = self.config['menu'][menu_name]['title']
						menu_item  = self.config['menu'][menu_name]['items'][position]['item']
						menu_text  = self.config['menu'][menu_name]['items'][position]['text']
						self.daemon.queue_signal('frontend',
						                         {'gui': {'screen': {'name': 'menu', 'parameter': {'title': menu_title, 'text': menu_text}}}})
						self.daemon.plugins['frontend'].menu_name = menu_name
						self.daemon.plugins['frontend'].menu_item = menu_item
					if 'select' in signal['control']:
						self.daemon.cancel_signal('menu:timeout')
						if menu_item.startswith('item-'):
							plugin = self.config['handlers'][menu_item]['plugin']
							signal = self.config['handlers'][menu_item]['signal']
							if isinstance(signal, dict):
								self.daemon.queue_signal(plugin, signal)
							elif isinstance(signal, list):
								signals = signal
								for signal in signals:
									if isinstance(signal, dict) is True:
										self.daemon.queue_signal(plugin, signal)
									else:
										self.daemon.logger.error(f"[enclosure/control]: unsupported signal type " \
										                         f"'{type(signal)}' in list of signals for menu " \
										                         f"item '{menu_item}': {signal}")
							else:
								self.daemon.logger.error(f"[enclosure/control]: unsupported signal type " \
								                         f"'{type(signal)}' in menu item '{menu_item}': {signal}")
						if menu_item.startswith('menu-'):
							menu_title = self.config['menu'][menu_item]['title']
							menu_text  = self.config['menu'][menu_item]['items'][0]['text']
							self.daemon.queue_signal('frontend',
							                         {'gui': {'screen': {'name': 'menu',
							                                             'parameter': {'title': menu_title, 'text': menu_text}}}})
							self.daemon.plugins['frontend'].menu_name = menu_item
							self.daemon.plugins['frontend'].menu_item = self.config['menu'][menu_item]['items'][0]['item']
							self.daemon.schedule_signal(self.config['menu']['timeout'],
							                            'frontend',
							                            {'gui': {'screen': {'name': 'idle', 'parameter': {}}}}, 'menu:timeout')
				case other:
					self.daemon.logger.error(f"[enclosure/control]: unknown screen '{self.daemon.plugins['frontend'].screen}', " \
					                         f"returning to screen 'idle'")
					self.daemon.queue_signal('frontend', {'gui': {'screen': {'name': 'idle', 'parameter': {}}}})

