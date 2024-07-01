#!/usr/bin/env python3

from json import loads as json_loads
from configparser import ConfigParser

from hal9000.brain.plugin import HAL9000_Plugin_Cortex
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
			self.load_menu(menu_config, 'menu-main')
		self.daemon.cortex['plugin']['frontend'].addNames(['menu_item', 'menu_name'])
		self.daemon.cortex['plugin']['frontend'].addNameCallback(self.on_frontend_screen_callback, 'screen')
		self.daemon.cortex['plugin']['enclosure'].addSignalHandler(self.on_enclosure_signal)


	def load_menu(self, menu_config: ConfigParser, menu_self: str) -> None:
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
					self.load_menu(menu_config, menu_entry)


	def on_frontend_screen_callback(self, plugin, key, old_value, new_value):
		if old_value == 'menu':
			self.daemon.cortex['plugin']['frontend'].menu_name = None
			self.daemon.cortex['plugin']['frontend'].menu_item = None
		return True


	async def on_enclosure_signal(self, plugin, signal):
		if 'control' in signal:
			self.daemon.add_timeout(self.config['menu']['timeout'], 'frontend:gui/screen', 'idle')
			if 'cancel' in signal['control']:
				await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
				return
			if 'delta' in signal['control']:
				if self.daemon.cortex['plugin']['frontend'].screen == HAL9000_Plugin_Cortex.UNINITIALIZED:
					self.daemon.cortex['plugin']['frontend'].screen = 'idle'
				if self.daemon.cortex['plugin']['frontend'].screen not in ['idle', 'menu']: # TODO
					return
				if self.daemon.cortex['plugin']['frontend'].screen == 'idle':
					self.daemon.cortex['plugin']['frontend'].screen = 'menu'
				if self.daemon.cortex['plugin']['frontend'].menu_name == HAL9000_Plugin_Cortex.UNINITIALIZED:
					self.daemon.cortex['plugin']['frontend'].menu_name = 'menu-main'
					self.daemon.cortex['plugin']['frontend'].menu_item = self.config['menu']['menu-main']['items'][0]['item']
					signal['control']['delta'] = 0
				menu_name = self.daemon.cortex['plugin']['frontend'].menu_name
				menu_item = self.daemon.cortex['plugin']['frontend'].menu_item
				if menu_name not in self.config['menu']:
					await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'overlay': {'name': 'error', 'parameter': {'text': "Error in menu"}}}}) #TODO
					return
				position = 0
				for item in self.config['menu'][menu_name]['items']:
					if item['item'] == menu_item:
						position = self.config['menu'][menu_name]['items'].index(item)
				position += int(signal['control']['delta'])
				position %= len(self.config['menu'][menu_name]['items'])
				menu_title = self.config['menu'][menu_name]['title']
				menu_item  = self.config['menu'][menu_name]['items'][position]['item']
				menu_text  = self.config['menu'][menu_name]['items'][position]['text']
				await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'menu', 'parameter': {'title': menu_title, 'text': menu_text}}}})
				self.daemon.cortex['plugin']['frontend'].menu_name = menu_name
				self.daemon.cortex['plugin']['frontend'].menu_item = menu_item
			if 'select' in signal['control']:
				if self.daemon.cortex['plugin']['frontend'].screen in ['error', 'qrcode']:
					self.daemon.del_timeout('frontend:gui/screen')
					await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
				if self.daemon.cortex['plugin']['frontend'].screen == 'menu':
					if self.daemon.cortex['plugin']['frontend'].menu_name == HAL9000_Plugin_Cortex.UNINITIALIZED:
						self.daemon.del_timeout('frontend:gui/screen')
						await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'idle', 'parameter': {}}}})
						return
					menu_item = self.daemon.cortex['plugin']['frontend'].menu_item
					if menu_item is not None:
						if menu_item.startswith('item-'):
							if menu_item not in self.config['handlers'] or 'plugin' not in self.config['handlers'][menu_item] or 'signal' not in self.config['handlers'][menu_item]:
								await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'error', 'parameter': {'menu': f"TODO:{menu_item}"}}}}) # TODO
								self.daemon.logger.error(f"plugin enclosure: invalid menu item '{menu_item}', check configuration (required: 'plugin' and 'signal')")
								return
							plugin_name = self.config['handlers'][menu_item]['plugin']
							signal_data = self.config['handlers'][menu_item]['signal']
							if plugin_name not in self.daemon.cortex['plugin']:
								await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'error', 'parameter': {'menu': f"TODO:{menu_item}"}}}})
								self.daemon.logger.error(f"plugin enclosure: unknown plugin '{menu_item}', check configuration")
								return
							await self.daemon.cortex['plugin'][plugin_name].signal(json_loads(signal_data))
							self.daemon.del_timeout('frontend:gui/screen')
						elif menu_item.startswith('menu-'):
							if menu_item not in self.config['menu']:
								await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'error', 'parameter': {'menu': f"TODO:{menu_item}"}}}})
								self.daemon.logger.error(f"plugin enclosure: invalid menu item '{menu_item}', check configuration")
								return
							menu_title = self.config['menu'][menu_item]['title']
							menu_text  = self.config['menu'][menu_item]['items'][0]['text']
							await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'menu', 'parameter': {'title': menu_title, 'text': menu_text}}}})
							self.daemon.cortex['plugin']['frontend'].menu_name = menu_item
							self.daemon.cortex['plugin']['frontend'].menu_item = self.config['menu'][menu_item]['items'][0]['item']
						else:
							await self.daemon.cortex['plugin']['frontend'].signal({'gui': {'screen': {'name': 'error', 'parameter': {'menu': f"TODO:{menu_item}"}}}})
							self.daemon.logger.error(f"plugin enclosure: invalid menu item '{menu_item}', check configuration")
							return

