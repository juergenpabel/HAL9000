import time
import flet


class Screen(flet.Container):

	def __init__(self) -> None:
		super().__init__(width=750, height=500)
		self.border_radius = flet.border_radius.all(10)


	def setContext(self, page: flet.Page, parent: flet.AnimatedSwitcher):
		self.screen_page = page
		self.screen_parent = parent


	def on_show(self, e: flet.ContainerTapEvent):
		self.screen_parent.content.content = flet.Image(src=e.control.content.src, fit=flet.ImageFit.FILL, border_radius=flet.border_radius.all(10))
		self.screen_page.update()
		time.sleep(1)
		self.screen_parent.content = self
		self.screen_page.update()

