from configparser import ConfigParser
from hal9000.brain import HAL9000_Abstract


class HAL9000_Plugin_Cortex(object):
	UNINITIALIZED = '<uninitialized>'
	SPECIAL_NAMES = ['plugin_id', 'valid_names', 'callbacks_data', 'callbacks_signal']

	def __init__(self, plugin_id: str, **kwargs):
		self.plugin_id = plugin_id
		self.valid_names = ['state']
		self.valid_names.extend(kwargs.get('valid_names', []))
		for name in self.valid_names:
			super().__setattr__(name, kwargs.get(name, HAL9000_Plugin_Cortex.UNINITIALIZED))
		for name, value in kwargs.items():
			if name in self.valid_names:
				super().__setattr__(name, value)
		self.callbacks_data = { '*': set() }
		self.callbacks_signal = set()


	def addNames(self, valid_names: list):
		for name in valid_names:
			if name not in HAL9000_Plugin_Cortex.SPECIAL_NAMES:
				self.valid_names.append(name)
				super().__setattr__(name, HAL9000_Plugin_Cortex.UNINITIALIZED)

	def addNameCallback(self, callback, name='*'):
		if name not in self.callbacks_data:
			self.callbacks_data[name] = set()
		self.callbacks_data[name].add(callback)


	def delNameCallback(self, callback, name='*'):
		if name in self.callbacks_data:
			self.callbacks_data[name].remove(callback)


	def addSignalHandler(self, callback):
		self.callbacks_signal.add(callback)


	def delSignalHandler(self, callback, name='*'):
		self.callbacks_signal.remove(callback)


	def signal(self, data):
		for callback in self.callbacks_signal:
			callback(self, data)


	def __setattr__(self, name, new_value):
		if name in HAL9000_Plugin_Cortex.SPECIAL_NAMES:
			super().__setattr__(name, new_value)
			return
		if name not in self.valid_names:
			raise Exception(f"HAL9000_Plugin_Cortex.__setattr__('{name}', '{new_value}'): '{name}' is not a registered attribute name")
		old_value = None
		if hasattr(self, name) is True:
			old_value = getattr(self, name)
		if new_value is None:
			new_value = HAL9000_Plugin_Cortex.UNINITIALIZED
		if old_value != new_value:
			commit_value = True
			for callback_name in ['*', name]:
				if callback_name in self.callbacks_data:
					for callback in self.callbacks_data[callback_name]:
						commit_value &= callback(self, name, old_value, new_value)
			if commit_value is True:
				super().__setattr__(name, new_value)


	def __repr__(self):
		result = '{'
		for name in self.valid_names:
			value = getattr(self, name)
			if value != HAL9000_Plugin_Cortex.UNINITIALIZED:
				result += f'{name}=\'{getattr(self, name)}\', '
		if len(result) > 2:
			result = result[:-2]
		result += '}'
		return result


class HAL9000_Plugin(HAL9000_Abstract):
	PLUGIN_RUNLEVEL_UNKNOWN  = "unknown"
	PLUGIN_RUNLEVEL_STARTING = "starting"
	PLUGIN_RUNLEVEL_RUNNING  = "running"
	PLUGIN_RUNLEVEL_HALTING  = "halting"

	def __init__(self, plugin_type: str, plugin_class: str, plugin_name: str, plugin_cortex: HAL9000_Plugin_Cortex, **kwargs) -> None:
		HAL9000_Abstract.__init__(self, f"{plugin_type}:{plugin_class}:{plugin_name}")
		self.daemon = kwargs.get('daemon', None)
		if plugin_cortex is not None and self.daemon is not None:
			if plugin_class not in self.daemon.cortex['plugin']:
				self.daemon.cortex['plugin'][plugin_class] = plugin_cortex
		self.config = dict()


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		pass


	def runlevel(self) -> str:
		return HAL9000_Plugin.PLUGIN_RUNLEVEL_UNKNOWN


	def runlevel_error(self) -> dict:
		return {"code": "TODO",
		        "level": "error",
		        "message": "BUG: HAL9000_Plugin derived class did not implement runlevel_error()"}



class HAL9000_Action(HAL9000_Plugin):
	def __init__(self, action_class: str, action_name: str, plugin_cortex: HAL9000_Plugin_Cortex, **kwargs) -> None:
		HAL9000_Plugin.__init__(self, "action", action_class, action_name, plugin_cortex, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name)



class HAL9000_Trigger(HAL9000_Plugin):
	def __init__(self, trigger_class: str, trigger_name: str, plugin_cortex: HAL9000_Plugin_Cortex, **kwargs) -> None:
		HAL9000_Plugin.__init__(self, "trigger", trigger_class, trigger_name, plugin_cortex, **kwargs)


	def configure(self, configuration: ConfigParser, section_name: str) -> None:
		HAL9000_Plugin.configure(self, configuration, section_name, None)


	def runlevel(self) -> str:
		return HAL9000_Plugin.PLUGIN_RUNLEVEL_RUNNING


	def handle(self, message) -> dict:
		return None

