import time
import flet_core
import flet

from hal9000.dashboard.screen import Screen


class ScreenStart(Screen):

	def build(self):
		super().build()
		self.screen = flet.Column()
		self.screen.controls.append(flet.Row(controls=[flet.Text("HAL9000 Dashboard", size=20)], alignment=flet.MainAxisAlignment.CENTER))
		self.screen.controls.append(flet.Row(height=10))
		self.screen.controls.append(flet.Row(controls=[flet.Text("Click on the screens above (tooltips indicate their respective functionality).")],
		                                     alignment=flet.MainAxisAlignment.CENTER))
		self.content = self.screen

	def on_show(self, e: flet.ContainerTapEvent):
		self.screen_parent.content = flet.Column()
		self.screen_page.update()
		time.sleep(1)
		self.screen_parent.content = self
		self.screen_page.update()

