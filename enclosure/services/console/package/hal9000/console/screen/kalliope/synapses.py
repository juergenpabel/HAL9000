import os
import re
import json
import jsonpath_ng
import jsonpath_ng.ext
import requests

import flet
import flet_core.colors
import flet_core.icons

from . import ScreenKalliope


class ScreenSynapses(ScreenKalliope):

	signal_types = {
	    'mqtt_subscriber': {
	        'broker_ip':   {
	            'default': '127.0.0.1',
	            'regex': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
	            'error': 'Not a valid IPv4 address'},
	        'broker_port': {
	            'default': '1883',
	            'regex': r'^((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|([1-5][0-9]{4})|([0-5]{0,5})|([0-9]{1,4}))$',
	            'error': 'Not a valid TCP port number'},
	        'topic': {
	            'default': '',
	            'regex': r'.+',
	            'error': 'The MQTT topic must be at least one character long'}
	        },
	    'order': {
	        'text': {
	            'default': '',
	            'regex': r'\w[ \w(\{\{\w+\}\})]+\w',
	            'error': 'Orders must consist of at least two words using only alpha-numeric characters (and whitespaces between words)'
	        }
	    }
        }
	neuron_types = { 
	    'list_available_orders': {
	        'file_template': {
	            'default': '',
	            'regex': r'^.+$',
	            'error': 'A filename must be provided'
	        }
	    },
	    'mqtt_publisher': {
	        'broker_ip': {
	            'default': '127.0.0.1',
	            'regex': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
	            'error': 'Not a valid IPv4 address'
	        },
	        'port':      {
	            'default': '1883',
	            'regex': r'^((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|([1-5][0-9]{4})|([0-5]{0,5})|([0-9]{1,4}))$',
	            'error': 'Not a valid TCP port number'
	        },
	        'topic':     {
	            'default': '',
	            'regex': r'^.+$',
	            'error': 'The MQTT topic must be at least one character long'
	        },
	        'payload':   {
	            'default': '',
	            'regex': None,
	            'error': None
	        }
	    },
	    'neurotimer': {
	        'hours': {
	            'default': '0',
	            'regex': r'^(\d+|\{\{\w+\}\})$',
	            'error': 'A numerical value must be provided'
	        },
	        'minutes': {
	            'default': '0',
	            'regex': r'^(\d+|\{\{\w+\}\})$',
	            'error': 'A numerical value must be provided'
	        },
	        'seconds': {
	            'default': '0',
	            'regex': r'^(\d+|\{\{\w+\}\})$',
	            'error': 'A numerical value must be provided'
	        },
	        'synapse': {
	            'default': '',
	            'regex': r'(?=[a-zA-Z0-9\-]{4,100}$)^[a-zA-Z0-9]+(\-[a-zA-Z0-9]+)*$',
	            'error': 'A valid synampse name must consist of only alpha-numeric characters (and whitespaces between words)'
	        }
	    },
	    'play': {
	        'filename': {
	            'default': '',
	            'regex': r'^.+$',
	            'error': 'A filename must be provided'
	        }
	    },
	    'say': {
	        'message':  {
	            'default': '',
	            'regex': r'^\w[ \w(\{\{\w+\}\})]*\w*$',
	            'error': 'Messages must consist of only alpha-numeric characters (and whitespaces between words)'
	        }
	    },
	    'script': {
	        'path': {
	            'default': '',
	            'regex': r'^.+$',
	            'error': 'A filename must be provided'
	        }
	    },
	    'shell': {
	        'cmd': {
	            'default': '',
	            'regex': r'^.+$',
	            'error': 'A command must be provided'
	        }
	    },
	    'systemdate': {
	        'say_template':  {
	            'default': '',
	            'regex':   None,
	            'error':   None
	        },
	        'file_template': {
	            'default': '',
	            'regex':   None,
	            'error':   None
	        }
	    }
	}
	targets = {
	    'synapse': {
	        'type': 'dataclass', 'icon': flet_core.icons.FACT_CHECK, 'target:jsonpath': '$.synapses[*].name'
	    }
	}
	target_parameters = {
	    'synapse': {
	        'type': 'readonly', 'text': 'Parameters (JSON)', 'filter:jsonpath': '$.synapses[?(@.name==\'{filter}\')]'
	    }
	}


	def __init__(self):
		kalliope_server = os.getenv("KALLIOPE_SERVER", default="127.0.0.1")
		kalliope_port   = os.getenv("KALLIOPE_PORT",   default="5000")
		super().__init__("Synapses", True, f'http://{kalliope_server}:{kalliope_port}/synapses')


	def load_data(self):
		result = False
		try:
			result = super().load_data()
			if result is True:
				for synapse in self.data['synapses']:
					for signal in synapse['signals']:
						for name, parameter in signal.items():
							if name == 'order' and isinstance(parameter, str):
								signal['order'] = { 'text': parameter }
			self.data['synapses'].sort(key=lambda synapse: synapse['name'])
			hooks = []
			response = requests.get(f'{self.api_url[0:-9]}/settings/hooks')
			if response.ok is True:
				data = response.json()
				for key, value in data['hooks'].items():
					if isinstance(value, str):
						hooks.append(value)
			for synapse in self.data['synapses']:
				if synapse['name'] in hooks:
					synapse['hooked'] = True
				else:
					synapse['hooked'] = False
		except Exception as e:
			self.data = {}
		return result


	def save_data(self, id, data):
		synapse = {}
		synapse['name'] = data['name']
		synapse['signals'] = []
		synapse['neurons'] = []
		for signal in data['signals']:
			synapse['signals'].append({signal['name']: signal['parameters']})
		for neuron in data['neurons']:
			synapse['neurons'].append({neuron['name']: neuron['parameters']})
		try:
			if len(id) > 0:
				requests.delete(f'{self.api_url}/{id}')
			response = requests.post(self.api_url, json=synapse)
			if response.ok is False:
				raise RuntimeError(f"kalliope returned HTTP code {response.status_code} and body content={response.json()}")
		except Exception as e:
			self.show_error(f"Error saving synapse '{synapse['name']}': {str(e)}")
			return False
		return True

	def build(self):
		def build_update(event):
			visibility = False
			if event is not None:
				visibility = event.control.value
			for synapse in self.data['synapses']:
				if 'hooked' in synapse and synapse['hooked'] is True:
					for row in self.screen.controls[1].controls:
						if row.controls[0].data == synapse['name']:
							row.controls[1].color = flet_core.colors.GREY
							row.visible = visibility
			if event is not None:
				self.screen.update()
		super().build()
		if isinstance(self.data, dict) and 'synapses' in self.data and len(self.data['synapses']) > 0:
			self.screen.controls[0].controls.append(flet.Row(expand=True, alignment=flet.MainAxisAlignment.END,
			                                                 controls=[flet.Checkbox(label="Show system synapses", value=False, on_change=build_update)]))
			build_update(None)
		self.content = self.screen

	def on_create(self, event):
		synapse = { 'name': '', 'signals': [], 'neurons': []}
		self.data['synapses'].append(synapse)
		self.on_dataclass(event)
		synapse = self.data['synapses'][-1]
		self.screen.controls[1].controls.append(flet.Row(controls=[flet.IconButton(self.targets['synapse']['icon'], on_click=self.on_dataclass, data=''),
		                                                           flet.Text('')]))


	def on_dataclass(self, event):
		def delete(event):
			name = event.control.data
			try:
				response = requests.delete(f'{self.api_url}/{name}')
				if response.ok is False:
					raise RuntimeError(f"kalliope returned HTTP code {response.status_code} and body content={response.json()}")
				jsonpath_ng.ext.parse(self.target_parameters['synapse']['filter:jsonpath'].format(filter=name)).filter(lambda synapse: synapse['name']==name, self.data)
			except Exception as e:
				self.show_error(f"Error deleting synapse '{name}': {str(e)}")
				return
			self.page.close_dialog()
			self.page.update()
			for row in self.screen.controls[1].controls:
				if row.controls[0].data == name:
					row.controls[0].data = None
					row.visible = False
					self.screen.update()
		def cancel(event):
			if self.page.dialog.data == '':
				self.screen.controls[1].controls.pop()
				self.screen.update()
			self.page.close_dialog()
			self.page.update()
		def save(event):
			name = self.page.dialog.content.controls[1].value
			if self.page.dialog.data == '':
				if re.fullmatch(r'(?=[a-zA-Z0-9\-]{4,100}$)^[a-zA-Z0-9]+(\-[a-zA-Z0-9]+)*$', name) is None:
					self.show_error("A name must be at least 4 characters long and may only consist of alphanumeric characters and dashes (but not as a first or last character)")
					self.page.dialog.content.controls[1].focus()
					return
				if len(jsonpath_ng.ext.parse(self.target_parameters['synapse']['filter:jsonpath'].format(filter=name)).find(self.data)) > 0:
					self.show_error("A synapse with this name already exists, choose another name")
					self.page.dialog.content.controls[1].focus()
					return
			synapse = {}
			synapse['name'] = self.page.dialog.content.controls[1].value
			synapse['signals'] = []
			for column_signal in self.page.dialog.content.controls[4].controls:
				if column_signal.visible is True:
					signal_name = column_signal.controls[0].controls[1].value
					signal = {}
					signal['name'] = signal_name
					signal['parameters'] = {}
					for row in column_signal.controls[1:]:
						parameter_name = row.controls[0].label
						parameter_value = row.controls[0].value
						parameter_type = ScreenSynapses.signal_types[signal_name][parameter_name]
						if parameter_type['regex'] is not None:
							if re.fullmatch(parameter_type['regex'], parameter_value) is None:
								self.show_error(parameter_type['error'])
								row.controls[0].focus()
								return
						signal['parameters'][parameter_name] = parameter_value
					synapse['signals'].append(signal)
			synapse['neurons'] = []
			for column_neuron in self.page.dialog.content.controls[7].controls:
				if column_neuron.visible is True:
					neuron_name = column_neuron.controls[0].controls[1].value
					neuron = {}
					neuron['name'] = neuron_name
					neuron['parameters'] = {}
					for row in column_neuron.controls[1:]:
						parameter_name = row.controls[0].label
						parameter_value = row.controls[0].value
						parameter_type = ScreenSynapses.neuron_types[neuron_name][parameter_name]
						if parameter_type['regex'] is not None:
							if re.fullmatch(parameter_type['regex'], parameter_value) is None:
								self.show_error(parameter_type['error'])
								row.controls[0].focus()
								return
						neuron['parameters'][parameter_name] = parameter_value
					synapse['neurons'].append(neuron)
			if self.save_data(self.page.dialog.data, synapse) is False:
				self.show_error("failed to save synapse (kalliope API returned error)")
				return
			jsonpath_ng.ext.parse(self.target_parameters['synapse']['filter:jsonpath'].format(filter=self.page.dialog.data)).update(self.data, synapse)
			for row in self.screen.controls[1].controls:
				if row.controls[0].data == self.page.dialog.data:
					row.controls[0].data = synapse['name']
					row.controls[1].value = synapse['name']
					self.screen.update()
			self.page.close_dialog()
			self.page.update()
		def on_signal_add(event):
			dialog.content.controls[3].controls[1].disabled = True
			options = []
			for signal_name in ScreenSynapses.signal_types.keys():
				options.append(flet.dropdown.Option(signal_name))
			dialog.content.controls[3].controls.append(flet.Row(controls=[flet.Dropdown(options=options),
			                                                              flet.TextButton("OK", on_click=on_signal_create)]))
			self.page.update()
			dialog.content.controls[3].controls[-1].controls[0].focus()
		def on_signal_create(event):
			signal_name = dialog.content.controls[3].controls[-1].controls[0].value
			if signal_name not in ScreenSynapses.signal_types:
				self.show_error("A signal type must be selected")
				return
			dialog.content.controls[4].controls.append(make_signal_controls({'name': signal_name}, len(dialog.content.controls[4].controls)))
			del dialog.content.controls[3].controls[-1]
			dialog.content.controls[3].controls[1].disabled = False
			self.page.update()
		def on_signal_delete(event):
			dialog.content.controls[4].controls[event.control.data].visible = False
			self.page.update()
		def on_signal_blur(event):
			field_data = event.control.data
			if isinstance(field_data, dict) is True:
				if field_data['regex'] is not None:
					if re.fullmatch(field_data['regex'], event.control.value) is None:
						self.show_error(field_data['error'])
		def on_neuron_add(event):
			dialog.content.controls[6].controls[1].disabled = True
			options = []
			for neuron_name in ScreenSynapses.neuron_types.keys():
				options.append(flet.dropdown.Option(neuron_name))
			dialog.content.controls[6].controls.append(flet.Row(controls=[flet.Dropdown(options=options),
			                                                              flet.TextButton("OK", on_click=on_neuron_create)]))
			self.page.update()
			dialog.content.controls[6].controls[-1].controls[0].focus()
		def on_neuron_create(event):
			neuron_name = dialog.content.controls[6].controls[-1].controls[0].value
			if neuron_name not in ScreenSynapses.neuron_types:
				self.show_error("A neuron type must be selected")
				return
			dialog.content.controls[7].controls.append(make_neuron_controls({'name': neuron_name}, len(dialog.content.controls[7].controls)))
			del dialog.content.controls[6].controls[-1]
			dialog.content.controls[6].controls[1].disabled = False
			self.page.update()
		def on_neuron_delete(event):
			self.page.dialog.content.controls[7].controls[event.control.data].visible = False
			self.page.update()
		def on_neuron_blur(event):
			field_data = event.control.data
			if isinstance(field_data, dict) is True:
				if field_data['regex'] is not None:
					if re.fullmatch(field_data['regex'], event.control.value) is None:
						self.show_error(field_data['error'])
		def make_signal_controls(signal, identifier):
			signal_column = flet.Column()
			signal_column.controls.append(flet.Row(controls=[flet.Icon(name=flet_core.icons.PENDING_OUTLINED),
			                                                 flet.Text(value=signal['name'], expand=True),
			                                                 flet.IconButton(icon=flet_core.icons.DELETE, on_click=on_signal_delete, data=identifier)]))
			signal_name = signal['name']
			if signal_name in ScreenSynapses.signal_types:
				for field_name, field_data in ScreenSynapses.signal_types[signal_name].items():
					value = field_data['default']
					if 'parameters' in signal:
						if isinstance(signal['parameters'], dict):
							value = signal['parameters'].get(field_name, value)
						else:
							value = signal['parameters']
					signal_column.controls.append(flet.Row(controls=[flet.TextField(label=field_name, value=str(value), expand=True,
					                                                                on_blur=on_signal_blur, data=field_data)]))
			else:
				self.show_error(f"Unsupported signal type '{signal_name}', skipping")
				return
			return signal_column
		def make_neuron_controls(neuron, identifier):
			neuron_column = flet.Column()
			neuron_column.controls.append(flet.Row(controls=[flet.Icon(name=flet_core.icons.START),
			                                                 flet.Text(value=neuron['name'], expand=True),
			                                                 flet.IconButton(icon=flet_core.icons.DELETE, on_click=on_neuron_delete, data=identifier)]))
			neuron_name = neuron['name']
			if neuron_name in ScreenSynapses.neuron_types:
				for field_name, field_data in ScreenSynapses.neuron_types[neuron_name].items():
					value = field_data['default']
					if 'parameters' in neuron:
						if isinstance(neuron['parameters'], dict):
							value = neuron['parameters'].get(field_name, value)
						else:
							value = neuron['parameters']
					neuron_column.controls.append(flet.Row(controls=[flet.TextField(label=field_name, value=str(value), expand=True,
					                                                                on_blur=on_neuron_blur, data=field_data)]))
			else:
				self.show_error(f"Unsupported neuron '{neuron_name}', skipping")
				return
			return neuron_column
		def on_synapse_blur(event):
			if re.fullmatch(r'(?=[a-zA-Z0-9\-]{4,100}$)^[a-zA-Z0-9]+(\-[a-zA-Z0-9]+)*$', event.control.value) is None:
				self.show_error("A name must be at least 4 characters long and may only consist of alphanumeric characters and dashes (but not as a first or last character)")

		synapse = None
		for key, value in self.target_parameters.items():
			for synapse_match in jsonpath_ng.ext.parse(value['filter:jsonpath'].format(filter=event.control.data)).find(self.data):
				synapse = synapse_match.value
		if synapse is None:
			self.show_error(f"Internal error (bug): could not find (known) synapse '{event.control.data}' in memory")
			return
		dialog = flet.AlertDialog(modal=True, content_padding=None, inset_padding=flet.padding.symmetric(vertical=20, horizontal=12),
		                          content=flet.Column(height=650, width=650, scroll=flet_core.ScrollMode.AUTO),
		                                                          actions=[flet.TextButton("Cancel", on_click=cancel, data=event.control.data),
		                                                                   flet.TextButton("Save", on_click=save, data=event.control.data)],
		                                                          actions_alignment=flet.MainAxisAlignment.END)
		if event.control.data != '':
			dialog.actions.insert(0, flet.TextButton("Delete", on_click=delete, data=event.control.data))
		dialog.content.controls.append(flet.Row(height=1))
		dialog.content.controls.append(flet.TextField(label="Name", value=synapse['name'], autofocus=True,
		                                              disabled=True if len(synapse['name'])>0 else False,
		                                              on_blur=on_synapse_blur))
		dialog.content.controls.append(flet.Row(height=1))
		dialog.content.controls.append(flet.Row(controls=[flet.Text("Signals"), flet.IconButton(icon=flet_core.icons.ADD, on_click=on_signal_add)]))
		dialog.content.controls.append(flet.Column())
		for pos in range(len(synapse['signals'])):
			signal_controls = make_signal_controls(synapse['signals'][pos], pos)
			if signal_controls is not None:
				dialog.content.controls[4].controls.append(signal_controls)
		dialog.content.controls.append(flet.Row(height=1))
		dialog.content.controls.append(flet.Row(controls=[flet.Text("Neurons"), flet.IconButton(icon=flet_core.icons.ADD, on_click=on_neuron_add)]))
		dialog.content.controls.append(flet.Column())
		for pos in range(len(synapse['neurons'])):
			neuron_controls = make_neuron_controls(synapse['neurons'][pos], pos)
			if neuron_controls is not None:
				dialog.content.controls[7].controls.append(neuron_controls)
		dialog.data = event.control.data
		self.page.show_dialog(dialog)

