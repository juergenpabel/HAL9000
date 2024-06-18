#!/usr/bin/python3

import json
from datetime import datetime, timedelta
from configparser import ConfigParser

from hal9000.brain.daemon import Daemon, Activity
from hal9000.plugins.brain.enclosure import EnclosureComponent


class Control(EnclosureComponent):
	def __init__(self, **kwargs) -> None:
		EnclosureComponent.__init__(self, **kwargs)
		self.config['action'] = dict()
		self.config['menu'] = dict()
		self.config['menu']['menu-main'] = dict()
		self.config['menu']['menu-main']['title'] = ''
		self.config['menu']['menu-main']['items'] = list()


	def configure(self, configuration: ConfigParser, section_name: str, cortex: dict) -> None:
		EnclosureComponent.configure(self, configuration, section_name, cortex)
		if 'volume' not in cortex['enclosure']:
			cortex['enclosure']['control'] = dict()
		self.config['menu']['timeout'] = configuration.getint('enclosure:control', 'timeout', fallback=15)
		menu_files = configuration.getlist('enclosure:control', 'menu-files', fallback=[])
		item_files = configuration.getlist('enclosure:control', 'item-files', fallback=[])
		files = [file for file in menu_files+item_files if file is not None]
		if len(files) > 0:
			menu_config = ConfigParser()
			menu_config.read(files)
			self.load_menu(menu_config, 'menu-main')


	def load_menu(self, menu_config: ConfigParser, menu_self: str) -> None:
		self.config['menu'][menu_self]['title'] = menu_config.get(menu_self, 'title', fallback='')
		for menu_entry in menu_config.options(menu_self):
			if menu_entry.startswith('item-'):
				self.config['menu'][menu_self]['items'].append({'item': menu_entry, 'text': menu_config.get(menu_self, menu_entry)})
				self.config['action'][menu_entry] = dict()
				self.config['action'][menu_entry]['action-name'] = menu_config.get(menu_entry, 'action', fallback=None)
				self.config['action'][menu_entry]['signal-data'] = menu_config.get(menu_entry, 'signal-data', fallback=None)
			if menu_entry.startswith('menu-'):
				self.config['menu'][menu_self]['items'].append({'item': menu_entry, 'text': menu_config.get(menu_self, menu_entry)})
				if menu_entry not in self.config['menu']:
					self.config['menu'][menu_entry] = dict()
					self.config['menu'][menu_entry]['items'] = list()
					self.load_menu(menu_config, menu_entry)


	def process(self, signal: dict, cortex: dict) -> None:
		EnclosureComponent.process(self, signal, cortex)
		if 'brain' in signal:
			return
		if 'cancel' in signal['control']:
			self.daemon.video_gui_screen_show('idle', {})
			return
		if 'delta' in signal['control']:
			if cortex['#activity']['video'].screen not in ['idle', 'menu']: # TODO
				return
			if cortex['#activity']['video'].screen is None:          ## TODO
				cortex['#activity']['video'].screen = 'idle'     ## TODO
			if cortex['#activity']['video'].screen == 'idle':
				cortex['#activity']['video'].screen = 'menu'
				cortex['#activity']['video'].menu_name = 'none'
				cortex['#activity']['video'].menu_item = 'none'
			if cortex['#activity']['video'].menu_name == 'none':
				cortex['#activity']['video'].menu_name = 'menu-main'
				cortex['#activity']['video'].menu_item = self.config['menu']['menu-main']['items'][0]['item']
				signal['control']['delta'] = 0
			menu_name = cortex['#activity']['video'].menu_name
			menu_item = cortex['#activity']['video'].menu_item
			if menu_name not in self.config['menu']:
				self.daemon.video_gui_overlay_show('error', {'text': "Error in menu"})
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
			self.daemon.video_gui_screen_show('menu', {'title': menu_title, 'text': menu_text}, self.config['menu']['timeout'])
			cortex['#activity']['video'].menu_name = menu_name
			cortex['#activity']['video'].menu_item = menu_item
		if 'select' in signal['control']:
			if cortex['#activity']['video'].screen in ['error', 'qrcode']:
				self.daemon.video_gui_screen_show('idle', {})
			if cortex['#activity']['video'].screen == 'menu':
				if 'gui/screen' in self.daemon.timeouts:
					del self.daemon.timeouts['gui/screen']
				if cortex['#activity']['video'].menu_name == 'none':
					self.daemon.video_gui_screen_show('idle', {})
					return
				menu_item = cortex['#activity']['video'].menu_item
				cortex['#activity']['video'].menu_name = 'none'
				cortex['#activity']['video'].menu_item = 'none'
				if menu_item is not None:
					if menu_item.startswith('item-'):
						if menu_item not in self.config['action']:
							self.daemon.video_gui_screen_show('error', {'menu': f"TODO:{menu_item}"}, 10)
							self.daemon.logger.error(f"plugin enclosure: invalid menu item '{menu_item}', check configuration")
							return
						action_name = self.config['action'][menu_item]['action-name']
						if action_name not in self.daemon.actions:
							self.daemon.video_gui_screen_show('error', {'menu': f"TODO:{action_name}"}, 10)
							self.daemon.logger.error(f"plugin enclosure: invalid action '{action_name}', check configuration")
							return
						self.daemon.queue_signal(action_name, json.loads(self.config['action'][menu_item]['signal-data']))
						self.daemon.video_gui_screen_show('idle', {})
					elif menu_item.startswith('menu-'):
						if menu_item not in self.config['menu']:
							self.daemon.video_gui_screen_show('error', {'menu': f"TODO:{menu_item}"}, 10)
							self.daemon.logger.error(f"plugin enclosure: invalid menu item '{menu_item}', check configuration")
							return
						menu_title = self.config['menu'][menu_item]['title']
						menu_text  = self.config['menu'][menu_item]['items'][0]['text']
						self.daemon.video_gui_screen_show('menu', {'title': menu_title, 'text': menu_text}, self.config['menu']['timeout'])
						cortex['#activity']['video'].menu_name = menu_item
						cortex['#activity']['video'].menu_item = self.config['menu'][menu_item]['items'][0]['item']
					else:
						self.daemon.video_gui_screen_show('error', {'menu': f"TODO:{menu_item}"}, 10)
						self.daemon.logger.error(f"plugin enclosure: invalid menu item '{menu_item}', check configuration")
						return

