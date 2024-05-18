import flet
import flet_core.icons

from hal9000.console.screen import Screen


system_logs = {
               "HAL9000: Kalliope": "/var/log/uwsgi/app/kalliope.log",
                "HAL9000: Enclosure - Brain": "/var/log/uwsgi/app/enclosure-brain.log",
                "HAL9000: Enclosure - Arduino": "/var/log/uwsgi/app/enclosure-arduino.log",
                "HAL9000: Enclosure - Console": "/var/log/uwsgi/app/enclosure-console.log",
                "Linux: syslog": "/var/log/syslog",
                "Linux: messages": "/var/log/messages",
              }


class ScreenLogs(Screen):
	def __init__(self):
		super().__init__()


	def build(self):
		self.screen = flet.Column()
		self.screen.controls.append(flet.Text("Logs"))
		lv = flet.ListView(expand=True)
		for target, filename in system_logs.items():
			lv.controls.append(flet.Row(controls=[flet.IconButton(icon=flet_core.icons.FILE_OPEN, on_click=self.on_logfile, data=filename), flet.Text(target)]))
		self.screen.controls.append(lv)
		self.content = self.screen


	def on_logfile(self, event):
		def close(event):
			self.page.close_dialog()
		try:
			lv = flet.ListView(width=600)
			with open(event.control.data) as fp:
				lines = fp.readlines()
				for line in lines:
					lv.controls.append(flet.Text(line))
			self.page.show_dialog(flet.AlertDialog(title=flet.Text(event.control.data), modal=True, content=lv, actions=[flet.TextButton("Close", on_click=close)], actions_alignment=flet.MainAxisAlignment.END))
		except PermissionError:
			self.page.show_dialog(flet.AlertDialog(modal=True, content=flet.Text(f"Error opening file '{event.control.data}'"), actions=[flet.TextButton("OK", on_click=close)], actions_alignment=flet.MainAxisAlignment.END))

