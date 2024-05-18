import os
import json
import flet_core

from . import ScreenKalliope


class ScreenConfiguration(ScreenKalliope):

	targets = {
		   'player':  { 'type': 'select',   'icon': flet_core.icons.OUTPUT,       'text': 'Audio player',
	                        'target:jsonpath': '$.settings.default_player_name',  'target:api-identifier': 'default_player',
	                        'select:jsonpath': '$.settings.players[*].name'},
		   'trigger': { 'type': 'select',   'icon': flet_core.icons.WAVING_HAND,  'text': 'Trigger (wake-word)',
		                'target:jsonpath': '$.settings.default_trigger_name', 'target:api-identifier': 'default_trigger',
	                        'select:jsonpath': '$.settings.triggers[*].name'},
		   'stt':     { 'type': 'select',   'icon': flet_core.icons.TEXT_SNIPPET, 'text': 'Speech-to-text (STT)',
	                        'target:jsonpath': '$.settings.default_stt_name',     'target:api-identifier': 'default_stt',
	                        'select:jsonpath': '$.settings.stts[*].name'},
		   'tts':     { 'type': 'select',   'icon': flet_core.icons.VOICE_CHAT,   'text': 'Text-to-speech (TTS)',
	                        'target:jsonpath': '$.settings.default_tts_name', 'target:api-identifier': 'default_tts',
	                        'select:jsonpath': '$.settings.ttss[*].name'},
	       }
	target_parameters = {
		   'player':  { 'type': 'readonly', 'text': 'Parameters (JSON)',     'filter:jsonpath': '$.settings.players[?({filter})].parameters'},
		   'trigger': { 'type': 'readonly', 'text': 'Parameters (JSON)',     'filter:jsonpath': '$.settings.triggers[?({filter})].parameters'},
		   'stt':     { 'type': 'readonly', 'text': 'Parameters (JSON)',     'filter:jsonpath': '$.settings.ssts[?({filter})].parameters'},
		   'tts':     { 'type': 'readonly', 'text': 'Parameters (JSON)',     'filter:jsonpath': '$.settings.ttss[?({filter})].parameters'},
	}

	def __init__(self):
		kalliope_server = os.getenv("KALLIOPE_SERVER", default="127.0.0.1")
		kalliope_port   = os.getenv("KALLIOPE_PORT",   default="5000")
		super().__init__("Configuration", False, f'http://{kalliope_server}:{kalliope_port}/settings')

	def load_data(self):
		try:
			return super().load_data()
		except Exception:
			self.data = {}
		return False

	def save_data(self, name, value):
		if name is not None:
			try:
				return super().save_data(name, value)
			except Exception:
				#todo: logging
				pass
		return False

