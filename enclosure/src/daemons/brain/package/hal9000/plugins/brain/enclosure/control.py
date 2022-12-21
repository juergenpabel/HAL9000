#!/usr/bin/python3

import json
from datetime import datetime, timedelta
from configparser import ConfigParser

from hal9000.brain.daemon import Daemon
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
			cortex['enclosure']['control']['menu-name'] = None
			cortex['enclosure']['control']['menu-item'] = None
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
			if menu_entry.startswith("item-"):
				self.config['menu'][menu_self]['items'].append({"item": menu_entry, "text": menu_config.get(menu_self, menu_entry)})
				self.config['action'][menu_entry] = dict()
				self.config['action'][menu_entry]['action-name'] = menu_config.get(menu_entry, "action", fallback=None)
				self.config['action'][menu_entry]['signal-data'] = menu_config.get(menu_entry, "signal-data", fallback=None)
			if menu_entry.startswith("menu-"):
				self.config['menu'][menu_self]['items'].append({"item": menu_entry, "text": menu_config.get(menu_self, menu_entry)})
				if menu_entry not in self.config['menu']:
					self.config['menu'][menu_entry] = dict()
					self.config['menu'][menu_entry]['items'] = list()
					self.load_menu(menu_config, menu_entry)


	def process(self, signal: dict, cortex: dict) -> None:
		EnclosureComponent.process(self, signal, cortex)
		if 'cancel' in signal['control']:
			cortex['enclosure']['control']['menu-name'] = None
			cortex['enclosure']['control']['menu-item'] = None
			self.daemon.arduino_show_gui_screen('idle', {})
			return
		if 'delta' in signal['control']:
			if cortex['enclosure']['control']['menu-name'] is None:
				cortex['enclosure']['control']['menu-name'] = 'menu-main'
				cortex['enclosure']['control']['menu-item'] = self.config['menu']['menu-main']['items'][0]["item"]
				signal['control']['delta'] = 0
			menu_name = cortex['enclosure']['control']['menu-name']
			menu_item = cortex['enclosure']['control']['menu-item']
			if menu_name not in self.config['menu']:
				self.daemon.arduino_show_gui_overlay('error', {"text": "Error in menu"})
				return
			position = 0
			for item in self.config['menu'][menu_name]['items']:
				if item["item"] == menu_item:
					position = self.config['menu'][menu_name]['items'].index(item)
			position += int(signal['control']['delta'])
			position %= len(self.config['menu'][menu_name]['items'])
			menu_title = self.config['menu'][menu_name]['title']
			menu_item  = self.config['menu'][menu_name]['items'][position]["item"]
			menu_text  = self.config['menu'][menu_name]['items'][position]["text"]
			self.daemon.arduino_show_gui_screen('menu', {"title": menu_title, "text": menu_text})
			self.daemon.set_timeout(self.config['menu']['timeout'], 'action', ['enclosure', {"control": {"cancel": {}}}])
			cortex['enclosure']['control']['menu-name'] = menu_name
			cortex['enclosure']['control']['menu-item'] = menu_item
		if 'select' in signal['control']:
			if 'action' in self.daemon.timeouts:
				del self.daemon.timeouts['action']
			if cortex['enclosure']['control']['menu-name'] is not None:
				menu_item = cortex['enclosure']['control']['menu-item'] 
				cortex['enclosure']['control']['menu-name'] = None
				cortex['enclosure']['control']['menu-item'] = None
				if menu_item is not None:
					if menu_item.startswith("item-"):
						if menu_item not in self.config['action']:
							self.daemon.arduino_show_gui_screen('error', {"menu": "TODO:{}".format(menu_item)}, 10)
							self.daemon.logger.error("plugin enclosure: invalid menu item '{}', check configuration".format(menu_item))
							return
						action_name = self.config['action'][menu_item]["action-name"]
						if action_name not in self.daemon.actions:
							self.daemon.arduino_show_gui_screen('error', {"menu": "TODO"}, 10)
							self.daemon.logger.error("plugin enclosure: invalid action '{}', check configuration".format(action_name))
							return
						self.daemon.queue_action(action_name, json.loads(self.config['action'][menu_item]['signal-data']))
						self.daemon.arduino_show_gui_screen('idle', {})
					elif menu_item.startswith("menu-"):
						if menu_item not in self.config['menu']:
							self.daemon.arduino_show_gui_screen('error', {"menu": "TODO:{}".format(menu_item)}, 10)
							self.daemon.logger.error("plugin enclosure: invalid menu item '{}', check configuration".format(menu_item))
							return
						cortex['enclosure']['control']['menu-name'] = menu_item
						cortex['enclosure']['control']['menu-item'] = self.config['menu'][menu_item]['items'][0]["item"]
						menu_title = self.config['menu'][menu_item]['title']
						menu_text  = self.config['menu'][menu_item]['items'][0]["text"]
						self.daemon.arduino_show_gui_screen('menu', {"title": menu_title, "text": menu_text})
						self.daemon.set_timeout(self.config['menu']['timeout'], 'action', ['enclosure', {"control": {"cancel": {}}}])
					else:
						self.daemon.arduino_show_gui_screen('error', {"menu": "TODO:{}".format(menu_item)}, 10)
						self.daemon.logger.error("plugin enclosure: invalid menu item '{}', check configuration".format(menu_item))
						return

