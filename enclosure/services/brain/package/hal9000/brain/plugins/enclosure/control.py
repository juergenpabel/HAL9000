from json import loads as json_loads
from configparser import ConfigParser

from hal9000.brain.plugins.enclosure import EnclosureComponent


class Control(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config['handlers'] = dict()
		self.config['menu'] = dict()
		self.config['menu']['menu-main'] = dict()
		self.config['menu']['menu-main']['title'] = ''
		self.config['menu']['menu-main']['items'] = list()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		EnclosureComponent.configure(self, configuration, section_name)
		self.config['menu']['timeout'] = configuration.getint('enclosure:control', 'timeout', fallback=15)
		menu_files = configuration.getlist('enclosure:control', 'menu-files', fallback=[])
		item_files = configuration.getlist('enclosure:control', 'item-files', fallback=[])
		files = [file for file in menu_files+item_files if file is not None]
		if len(files) > 0:
			menu_config = ConfigParser()
			menu_config.read(files)
			self.configure_menu(menu_config, 'menu-main')
#TODO: validate menu config
#TODO		if menu_item not in self.config['handlers'] or 'plugin' not in self.config['handlers'][menu_item] or 'signal' not in self.config['handlers'][menu_item]:
#TODO			await self.daemon.plugins['frontend'].signal({'gui': {'screen': {'name': 'error', 'parameter': {'menu': f"TODO:{menu_item}"}}}}) # TODO
#TODO			self.daemon.logger.error(f"plugin enclosure: invalid menu item '{menu_item}', check configuration (required: 'plugin' and 'signal')")
#TODO			return
#TODO		if menu_item not in self.config['menu']:
#TODO			self.daemon.queue_signal('frontend',
#TODO			                         {'gui': {'screen': {'name': 'error',
#TODO			                                             'parameter': {'menu': f"TODO:{menu_item}"}}}})
#TODO			self.daemon.logger.error(f"plugin enclosure: invalid menu item '{menu_item}', check configuration")
#TODO			return
#TODO			if menu_name not in self.config['menu']:
#TODO				self.daemon.queue_signal('frontend',
#TODO				                         {'gui': {'overlay': {'name': 'error', 'parameter': {'text': "Error in menu"}}}}) #TODO
#TODO				return
		self.daemon.plugins['frontend'].addNames(['menu_item', 'menu_name'])
		self.daemon.plugins['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.plugins['enclosure'].addSignalHandler(self.on_enclosure_signal)


	def configure_menu(self, menu_config: ConfigParser, menu_self: str) -> None:
		self.config['menu'][menu_self]['title'] = menu_config.get(menu_self, 'title', fallback='')
		for menu_entry in menu_config.options(menu_self):
			if menu_entry.startswith('item-'):
				self.config['menu'][menu_self]['items'].append({'item': menu_entry, 'text': menu_config.get(menu_self, menu_entry)})
				self.config['handlers'][menu_entry] = dict()
				self.config['handlers'][menu_entry]['action'] = menu_config.get(menu_entry, 'action', fallback=None)
				self.config['handlers'][menu_entry]['plugin'] = menu_config.get(menu_entry, 'plugin', fallback=None)
				self.config['handlers'][menu_entry]['signal'] = menu_config.get(menu_entry, 'signal', fallback=None)
			if menu_entry.startswith('menu-'):
				self.config['menu'][menu_self]['items'].append({'item': menu_entry, 'text': menu_config.get(menu_self, menu_entry)})
				if menu_entry not in self.config['menu']:
					self.config['menu'][menu_entry] = dict()
					self.config['menu'][menu_entry]['items'] = list()
					self.configure_menu(menu_config, menu_entry)


	def on_frontend_screen_callback(self, plugin, key, old_value, new_value):
		if old_value == 'menu':
			self.daemon.plugins['frontend'].menu_name = None
			self.daemon.plugins['frontend'].menu_item = None
		return True


	async def on_enclosure_signal(self, plugin, signal):
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
						self.daemon.plugins['frontend'].menu_name = menu_name #TODO: menu_title?
						self.daemon.plugins['frontend'].menu_item = menu_item #TODO: menu_text?
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
							self.daemon.queue_signal(plugin, json_loads(signal))
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

