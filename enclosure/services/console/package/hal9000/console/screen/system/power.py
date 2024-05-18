from hal9000.console.screen import Screen

import os
import signal
import time
import flet
import flet_core
from paho.mqtt.publish import single as mqtt_publish_message

class ScreenPower(Screen):

	def __init__(self):
		super().__init__()

	def reboot(self, event):
		import logging
		for k,v in os.environ.items():
			logging.getLogger("uvicorn.error").error(f"ENV: {k} = {v}")
		try:
			mqtt_server = str(os.getenv('MQTT_SERVER', default='127.0.0.1'))
			mqtt_port   = int(os.getenv('MQTT_PORT', default='1883'))
			mqtt_publish_message('hal9000/command/brain/command', 'reboot', hostname=mqtt_server, port=mqtt_port)
			dialog = flet.AlertDialog(modal=True, content=flet.Text("Rebooting..."))
			self.page.show_dialog(dialog)
		except Exception:
			# if MQTT broker is not available, we're probably on a development system
			self.page.snack_bar = flet.SnackBar(flet.Text("Reboot not implemented in this runtime environment (no running MQTT broker)"))
			self.page.snack_bar.open = True
			self.page.update()

	def shutdown(self, event):
		dialog = flet.AlertDialog(modal=True, content=flet.Text("Shutting down..."))
		self.page.show_dialog(dialog)
		try:
			mqtt_server = str(os.getenv('MQTT_SERVER', default='127.0.0.1'))
			mqtt_port   = int(os.getenv('MQTT_PORT', default='1883'))
			mqtt_publish_message('hal9000/command/brain/command', 'poweroff', hostname=mqtt_server, port=mqtt_port)
			time.sleep(15)
			self.page.dialog.open = False
			self.page.snack_bar = flet.SnackBar(flet.Text("Shutdown not implemented in this runtime environment (no reaction upon shutdown request per MQTT)"))
			self.page.snack_bar.open = True
			self.page.update()
		except Exception:
			# if MQTT broker is not available, we're probably on a development system -> kill process
			os.kill(os.getpid(), signal.SIGTERM)

	def build(self):
		super().build()
		self.content = flet.Column(scroll=flet_core.ScrollMode.ALWAYS)
		self.content.controls.append(flet.Row(controls=[flet.Text("Power")]))
		self.content.controls.append(flet.Row(controls=[flet.TextButton("Shutdown", on_click=self.shutdown)]))
		self.content.controls.append(flet.Row(controls=[flet.TextButton("Reboot", on_click=self.reboot)]))

