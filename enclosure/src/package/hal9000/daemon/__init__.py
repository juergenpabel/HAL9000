#!/usr/bin/python3

import sys
import importlib
from configparser import ConfigParser

from .daemon import HAL9000_Daemon


class DaemonLoader():

	def __init__(self, filename):
		configuration = ConfigParser(delimiters='=', converters={'list': lambda list: [item.strip().strip('"').strip("'") for item in list.split(',')],
                                                                                 'string': lambda string: string.strip('"').strip("'")})
		configuration.read(filename)
		module_paths = configuration.getlist('python', 'module-paths', fallback=['.'])
		for module_path in module_paths:
		        sys.path.append(module_path)
		self.daemon_threads = configuration.getlist('daemon', 'threads', fallback=None)


	def import_daemon(self, module_name: str, class_name: str = None) -> HAL9000_Daemon:
		module = importlib.import_module(module_name)
		if module is not None:
			if class_name is None:
				class_name = 'Daemon'
			return getattr(module, class_name)
		return None

	def get_daemon_threads(self) -> list:
		return self.daemon_threads
