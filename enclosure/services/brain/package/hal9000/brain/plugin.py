from configparser import ConfigParser as configparser_ConfigParser


class HAL9000_Plugin_Status(object):
	UNINITIALIZED = '<uninitialized>'
	SPECIAL_NAMES = ['plugin_id', 'valid_names', 'callbacks_data', 'callbacks_signal']

	def __init__(self, plugin_id: str, **kwargs) -> None:
		self.plugin_id = plugin_id
		self.valid_names = ['runlevel', 'status']
		self.valid_names.extend(kwargs.get('valid_names', []))
		for name in self.valid_names:
			super().__setattr__(name, kwargs.get(name, HAL9000_Plugin_Status.UNINITIALIZED))
		for name, value in kwargs.items():
			if name in self.valid_names:
				super().__setattr__(name, value)
		self.callbacks_data = { '*': set() }
		self.callbacks_signal = set()


	def addNames(self, valid_names: list) -> None:
		for name in valid_names:
			if name not in HAL9000_Plugin_Status.SPECIAL_NAMES:
				self.valid_names.append(name)
				super().__setattr__(name, HAL9000_Plugin_Status.UNINITIALIZED)

	def addNameCallback(self, callback, name: str='*') -> None:
		if name not in self.callbacks_data:
			self.callbacks_data[name] = set()
		self.callbacks_data[name].add(callback)


	def delNameCallback(self, callback, name: str='*') -> None:
		if name in self.callbacks_data:
			self.callbacks_data[name].remove(callback)


	def addSignalHandler(self, callback) -> None:
		self.callbacks_signal.add(callback)


	def delSignalHandler(self, callback, name: str='*') -> None:
		self.callbacks_signal.remove(callback)


	async def signal(self, signal: dict) -> None:
		for callback in self.callbacks_signal:
			await callback(self, signal)


	def __setattr__(self, name: str, new_value) -> None:
		if name in HAL9000_Plugin_Status.SPECIAL_NAMES:
			super().__setattr__(name, new_value)
			return
		if name not in self.valid_names:
			raise Exception(f"HAL9000_Plugin_Status.__setattr__('{name}', '{new_value}'): '{name}' is not a registered attribute name")
		old_value = None
		if hasattr(self, name) is True:
			old_value = getattr(self, name)
		if new_value is None:
			new_value = HAL9000_Plugin_Status.UNINITIALIZED
		if old_value != new_value:
			commit_value = True
			for callback_name in ['*', name]:
				if callback_name in self.callbacks_data:
					for callback in self.callbacks_data[callback_name]:
						x = callback(self, name, old_value, new_value)
						if x is None:
							print(callback)
						else:
							commit_value &= x
#						commit_value &= callback(self, name, old_value, new_value)
			if commit_value is True:
				super().__setattr__(name, new_value)


	def __repr__(self) -> str:
		result = '{'
		for name in self.valid_names:
			value = getattr(self, name)
			if value != HAL9000_Plugin_Status.UNINITIALIZED:
				result += f'{name}=\'{getattr(self, name)}\', '
		if len(result) > 2:
			result = result[:-2]
		result += '}'
		return result


class HAL9000_Plugin(object):
	RUNLEVEL_UNKNOWN  = "unknown"
	RUNLEVEL_STARTING = "starting"
	RUNLEVEL_READY    = "ready"
	RUNLEVEL_RUNNING  = "running"

	def __init__(self, plugin_type: str, plugin_class: str, plugin_name: str, plugin_status: HAL9000_Plugin_Status, **kwargs) -> None:
		self.name = f"{plugin_type}:{plugin_class}:{plugin_name}"
		self.daemon = kwargs.get('daemon', None)
		if plugin_status is not None and self.daemon is not None:
			if plugin_class not in self.daemon.plugins:
				self.daemon.plugins[plugin_class] = plugin_status
		self.config = {}

	def __repr__(self) -> str:
		return self.name


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		pass


	def runlevel(self) -> str:
		return HAL9000_Plugin.RUNLEVEL_UNKNOWN


	def runlevel_error(self) -> dict:
		return {'id': '90',
		        'level': 'error',
		        'message': "BUG: HAL9000_Plugin derived class did not implement runlevel_error()"}



class HAL9000_Action(HAL9000_Plugin):
	def __init__(self, action_class: str, action_name: str, plugin_status: HAL9000_Plugin_Status, **kwargs) -> None:
		HAL9000_Plugin.__init__(self, "action", action_class, action_name, plugin_status, **kwargs)


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name)



class HAL9000_Trigger(HAL9000_Plugin):
	def __init__(self, trigger_class: str, trigger_name: str, plugin_status: HAL9000_Plugin_Status, **kwargs) -> None:
		HAL9000_Plugin.__init__(self, "trigger", trigger_class, trigger_name, plugin_status, **kwargs)


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name, None)


	def runlevel(self) -> str:
		return HAL9000_Plugin.RUNLEVEL_RUNNING


	def handle(self, data) -> dict:
		return {}

