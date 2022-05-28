#!/usr/bin/python3

import os
import sys
import time
import importlib

from configparser import ConfigParser

from . import HAL9000_Type


class HAL9000_Plugin(HAL9000_Type):
	def __init__(self, name: str) -> None:
		HAL9000_Type.__init__(self, name)
	def configure(self, configuration: ConfigParser, section: str) -> None:
		pass


class HAL9000_Action(HAL9000_Plugin):
	def __init__(self, name: str) -> None:
		HAL9000_Plugin.__init__(self, name)
	def process(self, data: dict) -> None:
		pass


class HAL9000_Trigger(HAL9000_Plugin):
	def __init__(self, name: str) -> None:
		HAL9000_Plugin.__init__(self, name)
	def handle(self) -> dict:
		return None


class HAL9000_PluginManager(HAL9000_Type):

	MODULE_TYPES = ['Action', 'Trigger']


	def __init__(self) -> None:
		HAL9000_Type.__init__(self, 'PluginManager')


	def load_action(self, module_name:str) -> HAL9000_Action:
		Action = self.__load_class('Action', module_name)
		if Action is not None:
			return Action()
		return None


	def load_trigger(self, module_name:str) -> HAL9000_Trigger:
		Trigger = self.__load_class('Trigger', module_name)
		if Trigger is not None:
			return Trigger()
		return None


	def __load_class(self, class_name: str, module_name: str) -> HAL9000_Plugin:
		module = importlib.import_module(module_name)
		if module is not None:
			return getattr(module, class_name)
		return None

