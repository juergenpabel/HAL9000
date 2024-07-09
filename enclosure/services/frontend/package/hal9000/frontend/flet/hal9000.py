from io import StringIO as io_StringIO
from os import getcwd as os_getcwd
from math import pi as math_pi, sin as math_sin, cos as math_cos
from json import dumps as json_dumps
from datetime import datetime as datetime_datetime
from logging import getLogger as logging_getLogger
from asyncio import Queue as asyncio_Queue, \
                    sleep as asyncio_sleep, \
                    create_task as asyncio_create_task, \
                    CancelledError as asyncio_CancelledError
from segno import make as segno_make

import flet
import flet.fastapi
import flet_core.alignment
from fastapi import FastAPI as fastapi_FastAPI

from hal9000.frontend import Frontend

class HAL9000(Frontend):

	def __init__(self, app: fastapi_FastAPI):
		super().__init__()
		self.flet_app = app
		self.command_session_queues = {}


	async def configure(self, configuration) -> bool:
		self.flet_app.mount('/', flet.fastapi.app(self.flet, route_url_strategy='path', assets_dir=f'{os_getcwd()}/assets'))
		return True


	async def start(self) -> None:
		await super().start()
		self.command_listener_task = asyncio_create_task(self.task_command_listener())


	async def task_command_listener(self):
		logging_getLogger('uvicorn').debug(f"[frontend:flet] starting command-listener (event-listeners are started per flet-session)")
		try:
			while self.command_listener_task.cancelled() is False:
				command = await self.commands.get()
				for command_session_queue in self.command_session_queues.values():
					command_session_queue.put_nowait(command.copy())
			logging_getLogger('uvicorn').debug(f"[frontend:flet] task_command_listener() cancelled")
		except asyncio_CancelledError as e:
			logging_getLogger('uvicorn').debug(f"[frontend:flet] task_command_listener() cancelled")
		logging_getLogger('uvicorn').info(f"[frontend:flet] exiting command-listener ('flet' frontend becomes non-functional)")
		self.command_listener_task = None


	async def run_command_session_listener(self, page, display):
		logging_getLogger('uvicorn').debug(f"[frontend:flet] starting command-listener for session '{page.session_id}'")
		try:
			command_session_queue = self.command_session_queues[page.session_id]
			command = await command_session_queue.get()
			while page.session_id in self.command_session_queues:
				logging_getLogger('uvicorn').debug(f"[frontend:flet] received command in session '{page.session_id}': {command}")
				match command['topic']:
					case 'application/runtime':
						if 'condition' in command['payload']:
							condition = command['payload']['condition']
							match condition:
								case 'awake':
									page.data['button_wakeup'].current.disabled = True
									page.data['button_sleep'].current.disabled = False
									page.update()
									self.show_idle(display)
								case 'asleep':
									page.data['button_wakeup'].current.disabled = False
									page.data['button_sleep'].current.disabled = True
									page.update()
									self.show_none(display)
								case other:
									logging_getLogger('uvicorn').warning(f"[frontend:flet] unsupported condition '{condition}' "
									                                     f"in command 'application/runtime'")
						if 'time' in command['payload']:
							if 'synced' in command['payload']['time']:
								display.data['idle_clock:synced'] = command['payload']['time']['synced']
						if 'shutdown' in command['payload'] and 'target' in command['payload']['shutdown']:
							target = command['payload']['shutdown']['target']
							match target:
								case 'poweroff':
									self.show_error(display, {'title': 'System shutdown',
									                          'message': f"Not supported for HTML",
									                          'code': 'TODO'})
								case 'reboot':
									self.show_error(display, {'title': 'System reboot',
									                          'message': f"Not supported for HTML",
									                          'code': 'TODO'})
								case other:
									logging_getLogger('uvicorn').warning(f"[frontend:flet] unsupported shutdown target '{target}' "
									                                     f"in command 'application/runtime'")
					case 'gui/screen':
						for screen in command['payload'].keys():
							match screen:
								case 'none':
									self.show_none(display)
								case 'idle':
									self.show_idle(display)
								case 'hal9000':
									self.show_hal9k(display, command['payload']['hal9000'])
								case 'menu':
									self.show_menu(display, command['payload']['menu'])
								case 'qrcode':
									self.show_qrcode(display, command['payload']['qrcode'])
								case 'error':
									self.show_error(display, command['payload']['error'])
								case other:
									self.show_error(display, {'title': "Unsupported screen",
									                          'message': screen,
									                          'code': 'TODO'})
									logging_getLogger('uvicorn').warning(f"[frontend:flet] unsupported screen '{screen}' "
									                                     f"in command 'gui/screen'")
					case 'gui/overlay':
						for overlay in command['payload'].keys():
							display.content.shapes = list(filter(lambda shape: shape.data!='overlay', display.content.shapes))
							match overlay:
								case 'none':
									display.content.update()
								case 'volume':
									radius = display.radius
									for level in range(0, int(command['payload']['volume']['level'])):
										color = 'white' if command['payload']['volume']['mute'] != 'true' else 'red'
										dx = math_cos(2*math_pi * level/100 * 6/8 + (2*math_pi*3/8));
										dy = math_sin(2*math_pi * level/100 * 6/8 + (2*math_pi*3/8));
										x1 = radius+(dx*radius*0.9)
										y1 = radius+(dy*radius*0.9)
										x2 = radius+(dx*radius*0.99)
										y2 = radius+(dy*radius*0.99)
										display.content.shapes.append(flet.canvas.Line(x1, y1, x2, y2,
										                                               paint=flet.Paint(color=color),
										                                               data='overlay'))
									display.content.update()
								case other:
									self.show_error(display, {'title': 'Unsupported overlay',
									                          'message': overlay,
									                          'code': 'TODO'})
									logging_getLogger('uvicorn').warning(f"[frontend:flet] unsupported overlay '{overlay}' "
									                                     f"in command 'gui/overlay'")
					case other:
						self.show_error(display, {'title': 'Unsupported command',
						                          'message': command['topic'],
						                          'code': 'TODO'})
						logging_getLogger('uvicorn').warning(f"[frontend:flet] unsupported command '{command['topic']}'")
				command = await command_session_queue.get()
		except Exception as e:
			logging_getLogger('uvicorn').error(f"[frontend:flet] exception in run_command_session_listener(): {e}")
		logging_getLogger('uvicorn').debug(f"[frontend:flet] exiting command-listener for session '{page.session_id}'")


	async def run_gui_screen_idle(self, page, display):
		while page.session_id in self.command_session_queues:
			clock = display.data['idle_clock'].current
			if clock is not None:
				clock.style.color='white' if display.data['idle_clock:synced'] is True else 'red'
				now = datetime_datetime.now()
				if now.second % 2 == 0:
					clock.text = now.strftime('%H:%M')
				else:
					clock.text = now.strftime('%H %M')
				display.content.update()
			await asyncio_sleep(1)


	async def run_gui_screen_hal9k(self, page, display):
		while page.session_id in self.command_session_queues:
			if len(display.data['hal9k_queue']) > 0:
				sequence = display.data['hal9k_queue'].pop(0)
				if sequence['name'] in ['wakeup', 'active', 'sleep']:
					display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
					for nr in range(0,10):
						display.background_image_src = f'/sequences/{sequence["name"]}/0{nr}.jpg'
						display.update()
						await asyncio_sleep(0.2)
				if sequence['name'] == 'sleep':
					display.background_image_src = '/sequences/init/00.jpg'
					display.update()
					self.events.put_nowait({'topic': 'gui/event', 'payload': {'screen': 'idle'}})
					self.show_idle(display)
			await asyncio_sleep(0.1)


	def show_none(self, display):
		display.content.shapes = []
		display.content.update()


	def show_idle(self, display):
		display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
		display.content.shapes.append(flet.canvas.Text(ref=display.data['idle_clock'],
		                                               x=int(display.radius), y=int(display.radius),
		                                               style=flet.TextStyle(size=int(display.page.scale*22)+2,
		                                                                    color='white' if display.data['idle_clock:synced'] is True else 'red'),
		                                               alignment=flet_core.alignment.center))
		display.content.update()


	def show_hal9k(self, display, data):
		display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
		if 'queue' in data:
			if data['queue'] == 'replace':
				display.data['hal9k_queue'].clear()
				display.data['hal9k_queue'].append(data['sequence'])
			elif data['queue'] == 'append':
				display.data['hal9k_queue'].append(data['sequence'])


	def show_menu(self, display, data):
		display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
		display.content.shapes.append(flet.canvas.Text(text=data['title'],
		                                               x=int(display.radius), y=int(0.5*display.radius),
		                                               style=flet.TextStyle(size=int(display.page.scale*18), color='white'),
		                                               alignment=flet_core.alignment.center))
		display.content.shapes.append(flet.canvas.Text(text=data['text'],
		                                               x=int(display.radius), y=int(display.radius),
		                                               style=flet.TextStyle(size=int(display.page.scale*18)+4, color='white'),
		                                               alignment=flet_core.alignment.center))
		display.content.update()


	def show_qrcode(self, display, data):
		display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
		display.content.shapes.append(flet.canvas.Text(text=data['title'],
		                                               x=int(display.radius), y=int(0.4*display.radius)-int((data['title-size'] if 'title-size' in data else 18)/2),
		                                               style=flet.TextStyle(color=data['title-color'] if 'title-color' in data else 'white',
		                                                                    size=int(display.page.scale*(data['title-size'] if 'title-size' in data else 18))),
		                                               alignment=flet_core.alignment.center))
		qrcode = io_StringIO()
		segno_make(data['url'], version=5, error='m').save(qrcode, kind='txt', border=1)
		qrcode.seek(0)
		box_size = int(display.radius/(37+2))
		box_offset = (display.radius-(37+2)*box_size)/2
		for y, line in enumerate(qrcode.readlines()):
			for x, value in enumerate(line.strip()):
				display.content.shapes.append(flet.canvas.Rect(x=box_offset+x*box_size+display.radius/2, y=box_offset+y*box_size+display.radius/2,
				                                               width=box_size, height=box_size,
				                                               paint=flet.Paint(color='white' if value == '0' else 'black')))
		display.content.shapes.append(flet.canvas.Text(text=data['hint'],
		                                               x=int(display.radius), y=int(1.75*display.radius)-int((data['hint-size'] if 'hint-size' in data else 14)/2),
		                                               style=flet.TextStyle(color=data['hint-color'] if 'hint-color' in data else 'white',
		                                                                    size=int(display.page.scale*(data['hint-size'] if 'hint-size' in data else 14))),
		                                               alignment=flet_core.alignment.center))
		display.content.update()


	def show_error(self, display, data):
		self.show_qrcode(display, {'title': data['message'], 'title-size': 10, 'title-color': 'red',
		                           'url': data['url'] if 'url' in data else 'https://github.com/juergenpabel/HAL9000/wiki/Error-database',
		                           'hint': f"Error {data['code']}", 'hint-size': 14, 'hint-color': 'red'})


	def on_button_wakeup(self, event):
		self.events.put_nowait({'topic': 'hal9000/command/brain/status', 'payload': 'awake'})

	def on_button_sleep(self, event):
		self.events.put_nowait({'topic': 'hal9000/command/brain/status', 'payload': 'asleep'})

	def on_control_up(self, event):
		self.events.put_nowait({'topic': 'device/event', 'payload': '{"device": {"type": "rotary", "name": "control"}, "event": {"delta": "+1"}}'})

	def on_control_down(self, event):
		self.events.put_nowait({'topic': 'device/event', 'payload': '{"device": {"type": "rotary", "name": "control"}, "event": {"delta": "-1"}}'})

	def on_control_select(self, event):
		self.events.put_nowait({'topic': 'device/event', 'payload': '{"device": {"type": "button", "name": "control"}, "event": {"status": "clicked"}}'})

	def on_volume_up(self, event):
		self.events.put_nowait({'topic': 'device/event', 'payload': '{"device": {"type": "rotary", "name": "volume"}, "event": {"delta": "+1"}}'})

	def on_volume_down(self, event):
		self.events.put_nowait({'topic': 'device/event', 'payload': '{"device": {"type": "rotary", "name": "volume"}, "event": {"delta": "-1"}}'})

	def on_volume_mute(self, event):
		self.events.put_nowait({'topic': 'device/event', 'payload': '{"device": {"type": "button", "name": "volume"}, "event": {"status": "clicked"}}'})


	def flet_on_disconnect(self, event):
		logging_getLogger('uvicorn').info(f"[frontend:flet] terminating flet session '{event.page.session_id}'")
		if event.page.session_id in self.command_session_queues:
			command_session_queue = self.command_session_queues[event.page.session_id]
			del self.command_session_queues[event.page.session_id]
			command_session_queue.put_nowait(None)
			if len(self.command_session_queues) == 0:
				self.status = Frontend.FRONTEND_STATUS_OFFLINE
				self.events.put_nowait({'topic': 'status', 'payload': self.status})
		

	async def flet(self, page: flet.Page):
		logging_getLogger('uvicorn').info(f"[frontend:flet] starting new flet session '{page.session_id}'")
		page.on_disconnect = self.flet_on_disconnect
		page.title = "HAL9000"
		page.theme_mode = flet.ThemeMode.DARK
		page.scale = page.height / 1000
		page.padding = 0
		page.data = {}
		page.data['button_sleep'] = flet.Ref[flet.TextButton]()
		page.data['button_wakeup'] = flet.Ref[flet.TextButton]()
		display = flet.CircleAvatar(radius=page.scale*120, bgcolor='black')
		display.content = flet.canvas.Canvas(width=display.radius*2, height=display.radius*2)
		display.background_image_src = '/sequences/init/00.jpg'
		display.data = {}
		display.data['idle_clock'] = flet.Ref[flet.canvas.Text]()
		display.data['idle_clock:synced'] = None
		display.data['hal9k_queue'] = []
		display.page = page
		page.add(flet.Row(controls=[flet.Column(controls=[
		                                                  flet.TextButton("Ctrl+", on_click=self.on_control_up),
		                                                  flet.TextButton("Select", on_click=self.on_control_select),
		                                                  flet.TextButton("Ctrl-", on_click=self.on_control_down),
		                                                 ], height=page.scale*960),
		                            flet.Column(controls=[
		                                                  flet.Container(content=flet.Column(controls=[
		                                                                                               flet.Row(height=page.scale*100, spacing=0),
		                                                                                               flet.Row(controls=[
		                                                                                                                  flet.TextButton(ref=page.data['button_sleep'], text="Sleep",
		                                                                                                                                  on_click=self.on_button_sleep),
		                                                                                                                  flet.TextButton(ref=page.data['button_wakeup'], text="Wakeup",
		                                                                                                                                  on_click=self.on_button_wakeup),
		                                                                                                                  ], width=page.scale*328, height=page.scale*340, spacing=0,
		                                                                                                                     vertical_alignment=flet.CrossAxisAlignment.START,
		                                                                                                                     alignment=flet.MainAxisAlignment.SPACE_EVENLY),
		                                                                                               flet.Row(controls=[display],
		                                                                                                        alignment=flet.MainAxisAlignment.CENTER,
		                                                                                                        vertical_alignment=flet.CrossAxisAlignment.START,
		                                                                                                        width=page.scale*328, height=page.scale*520, spacing=0),
		                                                                                              ], height=page.scale*960, spacing=0),
		                                                                 width=page.scale*328, height=page.scale*960, padding=0,
		                                                                 image_src="/HAL9000.jpg", image_fit=flet.ImageFit.FILL),
		                                                  ], spacing=0),
		                            flet.Column(controls=[
		                                                  flet.TextButton("Vol+", on_click=self.on_volume_up),
		                                                  flet.TextButton("Mute", on_click=self.on_volume_mute),
		                                                  flet.TextButton("Vol-", on_click=self.on_volume_down),
		                                                 ], height=page.scale*960),
		                           ], alignment=flet.MainAxisAlignment.CENTER, height=page.scale*960, spacing=0))
		page.update()
		self.command_session_queues[page.session_id] = asyncio_Queue()
		page.session.set('session_task', asyncio_create_task(self.run_command_session_listener(page, display)))
		page.session.set('gui_idle_task',asyncio_create_task(self.run_gui_screen_idle(page, display)))
		page.session.set('gui_hal9k_task', asyncio_create_task(self.run_gui_screen_hal9k(page, display)))
		self.show_none(display)
		self.status = Frontend.FRONTEND_STATUS_ONLINE
		self.events.put_nowait({'topic': 'status', 'payload': self.status})

