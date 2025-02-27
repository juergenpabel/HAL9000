from json import dumps as json_dumps
from configparser import ConfigParser as configparser_ConfigParser

from hal9000.brain.plugin import HAL9000_Action, HAL9000_Plugin, RUNLEVEL, CommitPhase


class Action(HAL9000_Action):

	def __init__(self, action_instance: str, **kwargs) -> None:
		super().__init__('mqtt', **kwargs)
		self.module.hidden = True
		self.runlevel = RUNLEVEL.RUNNING, CommitPhase.COMMIT


	def configure(self, configuration: configparser_ConfigParser, section_name: str) -> None:
		super().configure(configuration, section_name)
		self.module.daemon.plugins['mqtt'].addSignalHandler(self.on_mqtt_signal)


	async def on_mqtt_signal(self, plugin: str, signal: dict) -> None:
		if 'topic' in signal and 'payload' in signal:
			mqtt_topic = signal['topic']
			mqtt_payload = signal['payload']
			if isinstance(mqtt_payload, dict) is True:
				if 'trace' in signal:
					mqtt_payload['trace'] = signal['trace']
			if isinstance(mqtt_payload, str) is False:
				if mqtt_payload is None:
					mqtt_payload = ''
				else:
					mqtt_payload = json_dumps(mqtt_payload)
			self.module.daemon.mqtt_publish_queue.put_nowait({'topic': mqtt_topic, 'payload': mqtt_payload})

