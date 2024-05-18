import requests
import json
import jsonpath_ng
import jsonpath_ng.ext
import flet
import flet_core

from hal9000.console.screen import Screen


class ScreenKalliope(Screen):

	targets = None
	target_parameters = None

	def __init__(self, title: str, creatable: bool, api_url: str):
		super().__init__()
		self.title = title
		self.creatable = creatable
		self.api_url = api_url
		self.targets = self.__class__.targets
		self.target_parameters = self.__class__.target_parameters
		self.data = None

	def show_error(self, error):
		self.page.snack_bar = flet.SnackBar(content=flet.Text(error), duration=5000)
		self.page.snack_bar.open = True
		self.page.update()

	def load_data(self):
		response = requests.get(self.api_url)
		if response.ok is True:
			self.data = response.json()
		return response.ok

	def save_data(self, name, value):
		return requests.post(f'{self.api_url}/{name}', json={ name: value }).ok

	def build(self):
		super().build()
		self.screen = flet.Column(scroll=flet_core.ScrollMode.ALWAYS)
		self.screen.controls.append(flet.Row(controls=[flet.Text(self.title)]))
		if self.load_data() is False:
			self.screen.controls.append(flet.Row(controls=[flet.Icon(name=flet_core.icons.ERROR),
			                            flet.Text(f"Kalliope API not available ({self.api_url})")]))
			self.content = self.screen
			return
		if self.creatable is True:
			self.screen.controls[0].controls.append(flet.IconButton(icon=flet_core.icons.ADD, icon_size=16, on_click=self.on_create, data=''))
		lv = flet.ListView(expand=True)
		for key, value in self.targets.items():
			for target_match in jsonpath_ng.ext.parse(value['target:jsonpath']).find(self.data):
				if value['type'] == 'readonly':
					lv.controls.append(flet.Row(controls=[flet.IconButton(icon=value['icon']), flet.Text(f"{value['text']}: {target_match.value}")]))
				if value['type'] == 'bool':
					lv.controls.append(flet.Row(controls=[flet.IconButton(icon=value['icons'][str(target_match.value)], on_click=self.on_bool, data=key), flet.Text(value['text'])]))
				if value['type'] == 'select':
					lv.controls.append(flet.Row(controls=[flet.IconButton(icon=value['icon'], on_click=self.on_select, data=key), flet.Text(value['text'])]))
				if value['type'] == 'dataclass':
					lv.controls.append(flet.Row(controls=[flet.IconButton(icon=value['icon'], on_click=self.on_dataclass, data=target_match.value), flet.Text(target_match.value)]))
		self.screen.controls.append(lv)
		self.content = self.screen

	def on_create(self, event):
		raise NotImplementedError
		
	def on_bool(self, event):
		target_expr = jsonpath_ng.ext.parse(self.targets[event.control.data]['target:jsonpath'])
		for target_match in target_expr.find(self.data):
			value = not(target_match.value)
			if self.save_data(self.targets[event.control.data]['target:api-identifier'], value) is False:
				self.show_error("error returned from kalliope API")
				return
			event.control.icon = self.targets[event.control.data]['icons'][str(value)]
			target_match.full_path.update(self.data, value)
		event.control.update()

	def on_select(self, event):
		def on_select_changed(event):
			dialog.content.controls[3].value = '{}'
			parameter_expr = jsonpath_ng.ext.parse(self.target_parameters[dialog.data]['filter:jsonpath'].format(filter=f"@.name == '{dialog.content.controls[1].value}'"))
			for parameter_match in parameter_expr.find(self.data):
				dialog.content.controls[3].value = json.dumps(parameter_match.value)
			dialog.content.controls[3].update()
		def on_select_ok(event):
			target_expr = jsonpath_ng.ext.parse(self.targets[dialog.data]['target:jsonpath'])
			for target_match in target_expr.find(self.data):
				target_match.full_path.update(self.data, dialog.content.controls[1].value)
				if self.save_data(self.targets[dialog.data]['target:api-identifier'], dialog.content.controls[1].value) is False:
					self.show_error("error returned from kalliope API")
					return
			self.page.close_dialog()
			self.page.update()
		def on_select_cancel(event):
			self.page.close_dialog()
			self.page.update()
		dialog = flet.AlertDialog(content=flet.Column(), actions=[flet.TextButton("Cancel", on_click=on_select_cancel),
		                                                          flet.TextButton("OK", on_click=on_select_ok)],
		                          modal=True, actions_alignment=flet.MainAxisAlignment.END)
		dialog.content.controls.append(flet.Text(self.targets[event.control.data]['text']))
		options = []
		target_expr = jsonpath_ng.ext.parse(self.targets[event.control.data]['target:jsonpath'])
		for target_match in target_expr.find(self.data):
			select_expr = jsonpath_ng.ext.parse(self.targets[event.control.data]['select:jsonpath'])
			for select_match in select_expr.find(self.data):
				options.append(flet.dropdown.Option(select_match.value))
			dialog.content.controls.append(flet.Dropdown(options=options, value=target_match.value, on_change=on_select_changed))
			dialog.content.controls.append(flet.Text(self.target_parameters[event.control.data]['text']))
			dialog.content.controls.append(flet.TextField(disabled=True, value='{}', multiline=True, min_lines=8))
			parameter_expr = jsonpath_ng.ext.parse(self.target_parameters[event.control.data]['filter:jsonpath'].format(filter=f"@.name=='{target_match.value}'"))
			for parameter_match in parameter_expr.find(self.data):
				dialog.content.controls[3].value = json.dumps(parameter_match.value)
		dialog.data = event.control.data
		self.page.show_dialog(dialog)

	def on_datapass(self, event):
		raise NotImplementedError


from .synapses      import ScreenSynapses
from .configuration import ScreenConfiguration
from .status        import ScreenStatus

