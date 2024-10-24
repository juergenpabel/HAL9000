from io import StringIO as io_StringIO
from os import getcwd as os_getcwd, \
               readlink as os_readlink
from os.path import exists as os_path_exists, \
                    islink as os_path_islink, \
                    realpath as os_path_realpath
from math import pi as math_pi, sin as math_sin, cos as math_cos
from json import dumps as json_dumps, \
                 loads as json_loads, \
                 load as json_load
from configparser import ConfigParser as configparser_ConfigParser
from datetime import datetime as datetime_datetime
from asyncio import Queue as asyncio_Queue, \
                    sleep as asyncio_sleep, \
                    create_task as asyncio_create_task, \
                    CancelledError as asyncio_CancelledError
from segno import make as segno_make

import flet
import flet.fastapi as flet_fastapi
import flet_core.alignment as flet_core_alignment
from fastapi import FastAPI as fastapi_FastAPI
from fastapi.staticfiles import StaticFiles as fastapi_staticfiles_StaticFiles

from hal9000.frontend import Frontend, RUNLEVEL, STATUS

class HAL9000(Frontend):

	def __init__(self, app: fastapi_FastAPI) -> None:
		super().__init__('flet')
		self.flet_app = app
		self.environment = {}
		self.settings = {}
		self.gui_screen = 'none'
		self.gui_overlay = 'none'


	async def configure(self, configuration: configparser_ConfigParser) -> bool:
		await super().configure(configuration)
		resources_dir = f'{os_getcwd()}/resources'
		if os_path_islink(resources_dir) is True:
			resources_dir = os_path_realpath(resources_dir)
		self.flet_app.mount('/resources/', fastapi_staticfiles_StaticFiles(directory=resources_dir, follow_symlink=True), name="resources")
		self.flet_app.mount('/',           flet_fastapi.app(self.flet, route_url_strategy='path'))
		return True


	async def start(self) -> None:
		await super().start()
		self.status = STATUS.OFFLINE
		self.command_session_queues = {}
		self.tasks['command_listener'] = asyncio_create_task(self.task_command_listener())


	async def task_command_listener(self) -> None:
		self.logger.debug(f"[frontend:flet] starting command-listener (event-listeners are started per flet-session)")
		await asyncio_sleep(0.1)
		try:
			while self.tasks['command_listener'].cancelled() is False:
				command = await self.commands.get()
				for command_session_queue in self.command_session_queues.values():
					command_session_queue.put_nowait(command.copy())
		finally:
			self.logger.debug(f"[frontend:flet] task_command_listener() cancelled")
			del self.tasks['command_listener']
			self.runlevel = RUNLEVEL.DEAD
			return # ignore exception (return in finally block)


	async def run_command_session_listener(self, page: flet.page, display: flet.CircleAvatar) -> None:
		self.logger.debug(f"[frontend:flet] starting command-listener for session '{page.session_id}'")
		try:
			command_session_queue = self.command_session_queues[page.session_id]
			command = await command_session_queue.get()
			while page.session_id in self.command_session_queues:
				self.logger.debug(f"[frontend:flet] received command in session '{page.session_id}': {command}")
				match command['topic']:
					case 'system/runlevel':
						target = command['payload']
						match target:
							case 'halting':
								self.show_animations(display, {'name': 'system-terminating'})
							case 'restarting':
								self.show_animations(display, {'name': 'system-terminating'})
							case other:
								self.logger.warning(f"[frontend:flet] unsupported shutdown target '{target}' "
									            f"in command 'system/runlevel'")
					case 'system/features':
						if 'time' in command['payload']:
							if 'synced' in command['payload']['time']:
								page.session.set('idle_clock:synced', str(command['payload']['time']['synced']).lower())
						if 'display' in command['payload']:
							if 'backlight' in command['payload']['display']:
								match bool(command['payload']['display']['backlight']):
									case True:
										self.display_on(display)
									case False:
										self.display_off(display)
					case 'system/environment':
						if 'set' in command['payload']:
							if 'key' in command['payload']['set'] and 'value' in command['payload']['set']:
								key = command['payload']['set']['key']
								value = command['payload']['set']['value']
								self.environment[key] = value
								self.logger.debug(f"[frontend:flet] system/environment:set('{key}','{value}') => OK")
							else:
								self.logger.warning(f"[frontend:flet] for command 'system/environment' with 'set': " \
								                    f"missing 'key' and/or 'value' items: {command['payload']['set']}")
					case 'system/settings':
						if 'set' in command['payload']:
							if 'key' in command['payload']['set'] and 'value' in command['payload']['set']:
								key = command['payload']['set']['key']
								value = command['payload']['set']['value']
								self.settings[key] = value
								self.logger.debug(f"[frontend:flet] system/settings:set('{key}','{value}') => OK")
							else:
								self.logger.warning(f"[frontend:flet] for command 'system/settings' with 'set': " \
								                    f"missing 'key' and/or 'value' items: {command['payload']['set']}")
					case 'gui/screen':
						if isinstance(command['payload'], str) is True:
							if command['payload'] == '':
								self.events.put_nowait({'topic': 'gui/screen',
								                        'payload': {'screen': self.gui_screen, 'origin': 'frontend:flet'}})
						if isinstance(command['payload'], dict) is True:
							for screen in command['payload'].keys():
								match screen:
									case 'none':
										self.show_none(display)
									case 'idle':
										self.show_idle(display)
									case 'animations':
										self.show_animations(display, command['payload']['animations'])
									case 'menu':
										self.show_menu(display, command['payload']['menu'])
									case 'qrcode':
										self.show_qrcode(display, command['payload']['qrcode'])
									case 'splash':
										self.show_splash(display, command['payload']['splash'])
									case 'error':
										self.show_error(display, command['payload']['error'])
									case other:
										self.show_error(display, {'title': "BUG: unsupported screen",
										                          'detail': screen,
										                          'id': '922'})
										self.logger.warning(f"[frontend:flet] unsupported screen '{screen}' "
										                    f"in command 'gui/screen'")
					case 'gui/overlay':
						if isinstance(command['payload'], str) is True:
							if command['payload'] == '':
								self.events.put_nowait({'topic': 'gui/overlay',
								                        'payload': {'overlay': self.gui_overlay, 'origin': 'frontend:flet'}})
						if isinstance(command['payload'], dict) is True:
							for overlay in command['payload'].keys():
								if self.gui_screen != 'off' or overlay == 'none':
									display.content.shapes = list(filter(lambda shape: shape.data!='overlay', display.content.shapes))
									match overlay:
										case 'none':
											self.gui_overlay = 'none'
											display.content.update()
											self.events.put_nowait({'topic': 'gui/overlay',
											                        'payload': {'overlay': self.gui_overlay,
											                                    'origin': 'frontend:flet'}})
										case 'volume':
											if command['payload']['volume']['mute'] is False:
												self.gui_overlay = f'volume:{int(command["payload"]["volume"]["level"])}'
											else:
												self.gui_overlay = 'volume:mute'
											radius = display.radius
											for level in range(0, int(command['payload']['volume']['level'])):
												color = 'white' if command['payload']['volume']['mute'] is False else 'red'
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
											self.events.put_nowait({'topic': 'gui/overlay',
											                        'payload': {'overlay': self.gui_overlay,
											                        'origin': 'frontend:flet'}})
										case other:
											self.show_error(display, {'title': 'BUG: unsupported overlay',
											                          'detail': overlay,
											                          'id': '923'})
											self.logger.warning(f"[frontend:flet] unsupported overlay '{overlay}' "
											                    f"in command 'gui/overlay'")
					case other:
						self.show_error(display, {'title': 'BUG: Unsupported command',
						                          'detail': command['topic'],
						                          'id': '924'})
						self.logger.warning(f"[frontend:flet] unsupported command '{command['topic']}'")
				command = await command_session_queue.get()
		except Exception as e:
			self.logger.error(f"[frontend:flet] exception in run_command_session_listener(): {e}")
		self.logger.debug(f"[frontend:flet] exiting command-listener for session '{page.session_id}'")


	async def run_gui_screen_idle(self, page: flet.page, display: flet.CircleAvatar) -> None:
		while page.session_id in self.command_session_queues:
			if display.visible is True:
				if self.gui_screen == 'idle':
					clock = display.data['idle_clock'].current
					if clock is not None:
						if page.session.get("idle_clock:synced") == 'true':
							clock.style.color = 'white'
						else:
							clock.style.color = 'red'
						now = datetime_datetime.now()
						if now.second % 2 == 0:
							clock.text = now.strftime('%H:%M')
						else:
							clock.text = now.strftime('%H %M')
						display.content.update()
					await asyncio_sleep(0.9)
			await asyncio_sleep(0.1)


	async def run_gui_screen_animations(self, page: flet.page, display: flet.CircleAvatar) -> None:
		while page.session_id in self.command_session_queues:
			if display.visible is True:
				if self.gui_screen.startswith('animations:') is True:
					if 'name' in display.data['animations'] and 'json' in display.data['animations']:
						name = display.data['animations']['name']
						if len(display.data['animations']['json']) > 0:
							animation = display.data['animations']['json'].pop(0)
							if 'directory' in animation and 'frames' in animation and 'duration' in animation and 'loop' in animation:
								display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
								do_loop = True
								while do_loop is True and self.gui_screen.startswith('animations:'):
									for nr in range(0, animation['frames']):
										display.background_image_src = f'/resources{animation["directory"]}/{nr:02}.jpg'
										display.update()
										await asyncio_sleep((float(animation['duration'])/(animation['frames']*1000))+0.1)
									do_loop = bool(animation['loop'])
									if do_loop is True:
										animation_name = self.gui_screen.split(':',1).pop(1)
										if self.environment.get('gui/screen:animations/loop', '') == animation_name:
											del self.environment['gui/screen:animations/loop']
											do_loop = False
								display.background_image_src = '/resources/images/display.jpg'
								display.update()
							if 'on:next' in animation:
								if 'util/webserial:handle' in animation['on:next']:
									try:
										topic, payload = json_loads(animation['on:next']['util/webserial:handle'])
										self.commands.put_nowait({'topic': topic, 'payload': payload})
									except Exception as e:
										self.logger.error(f"[frontend:flet] on:next['util/webserial:handle'] in " \
										                  f"gui/screen:animations/{name} not webserial-compliant: " \
										                  f"'{animation['on:next']['util/webserial:handle']}' => {e}")
			await asyncio_sleep(0.1)


	def display_off(self, display: flet.CircleAvatar) -> None:
		display.content.visible = False
		display.content.update()


	def display_on(self, display: flet.CircleAvatar) -> None:
		display.content.visible = True
		display.content.update()


	def show_none(self, display: flet.CircleAvatar) -> None:
		self.gui_screen = 'none'
		display.content.shapes = []
		display.content.update()
		self.events.put_nowait({'topic': 'gui/screen', 'payload': {'screen': self.gui_screen,
		                                                           'display': {'backlight': display.visible},
		                                                           'origin': 'frontend:flet'}})


	def show_idle(self, display: flet.CircleAvatar) -> None:
		self.gui_screen = 'idle'
		display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
		display.content.shapes.append(flet.canvas.Text(ref=display.data['idle_clock'],
		                                               x=int(display.radius), y=int(display.radius),
		                                               style=flet.TextStyle(size=int(display.page.scale*22)+2),
		                                               alignment=flet_core_alignment.center))
		display.content.update()
		self.events.put_nowait({'topic': 'gui/screen', 'payload': {'screen': self.gui_screen,
		                                                           'display': {'backlight': display.visible},
		                                                           'origin': 'frontend:flet'}})


	def show_animations(self, display: flet.CircleAvatar, data: dict) -> None:
		self.gui_screen = f'animations:{data["name"]}'
		display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
		display.data['animations'] = {}
		if os_path_exists(f'resources/gui/screen/animations/{data["name"]}.json') is True:
			with open(f'resources/gui/screen/animations/{data["name"]}.json') as file:
				display.data['animations']['name'] = data['name']
				display.data['animations']['json'] = json_load(file)
		else:
			self.logger.error(f"[frontend:flet] file not found: 'resources/gui/screen/animations/{data['name']}.json'")
		display.content.update()
		self.events.put_nowait({'topic': 'gui/screen', 'payload': {'screen': self.gui_screen,
		                                                           'display': {'backlight': display.visible},
		                                                           'origin': 'frontend:flet'}})


	def show_menu(self, display: flet.CircleAvatar, data: dict) -> None:
		self.gui_screen = f'menu:{data["name"]}'
		display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
		display.content.shapes.append(flet.canvas.Text(text=data['title'],
		                                               x=int(display.radius), y=int(0.5*display.radius),
		                                               style=flet.TextStyle(size=int(display.page.scale*18), color='white'),
		                                               alignment=flet_core_alignment.center))
		display.content.shapes.append(flet.canvas.Text(text=data['text'],
		                                               x=int(display.radius), y=int(display.radius),
		                                               style=flet.TextStyle(size=int(display.page.scale*18)+4, color='white'),
		                                               alignment=flet_core_alignment.center))
		display.content.update()
		self.events.put_nowait({'topic': 'gui/screen', 'payload': {'screen': self.gui_screen,
		                                                           'display': {'backlight': display.visible},
		                                                           'origin': 'frontend:flet'}})


	def show_qrcode(self, display: flet.CircleAvatar, data: dict) -> None:
		self.gui_screen = 'qrcode'
		self.render_qrcode(display, data)
		self.events.put_nowait({'topic': 'gui/screen', 'payload': {'screen': self.gui_screen,
		                                                           'display': {'backlight': display.visible},
		                                                           'origin': 'frontend:flet'}})


	def show_splash(self, display: flet.CircleAvatar, data: dict) -> None:
		self.gui_screen = 'splash'
		self.render_qrcode(display, {'title': data['title'], 'title-size': int(display.page.scale*18), 'bg-color': 'blue', 'title-color': 'white',
		                             'url': data['url'] if 'url' in data else 'https://github.com/juergenpabel/HAL9000/wiki/Splash-database',
		                             'hint': f"Splash ID: {data['id']}", 'hint-size': int(display.page.scale*24), 'hint-color': 'white'})
		self.events.put_nowait({'topic': 'gui/screen', 'payload': {'screen': self.gui_screen,
		                                                           'display': {'backlight': display.visible},
		                                                           'origin': 'frontend:flet'}})


	def show_error(self, display: flet.CircleAvatar, data: dict) -> None:
		self.gui_screen = f'error:{data["id"]}'
		self.display_on(display) # this is a hack vs. how arduino handles display with backlight turned off
		self.render_qrcode(display, {'title': data['title'], 'title-size': int(display.page.scale*18), 'bg-color': 'red', 'title-color': 'white',
		                             'url': data['url'] if 'url' in data else 'https://github.com/juergenpabel/HAL9000/wiki/Error-database',
		                             'hint': f"Error {data['id']}", 'hint-size': int(display.page.scale*24), 'hint-color': 'white'})
		self.events.put_nowait({'topic': 'gui/screen', 'payload': {'screen': self.gui_screen,
		                                                           'display': {'backlight': display.visible},
		                                                           'origin': 'frontend:flet'}})


	def render_qrcode(self, display: flet.CircleAvatar, data: dict) -> None:
		display.content.shapes = list(filter(lambda shape: shape.data=='overlay', display.content.shapes))
		display.content.shapes.append(flet.canvas.Circle(x=display.radius, y=display.radius, radius=display.radius,
		                                                 paint=flet.Paint(color=data['bg-color'] if 'bg-color' in data else 'black')))
		display.content.shapes.append(flet.canvas.Text(text=data['title'],
		                                               x=display.radius, y=int(0.5*display.radius)-int((data['title-size'] if 'title-size' in data else 18)/2),
		                                               style=flet.TextStyle(color=data['title-color'] if 'title-color' in data else 'white',
		                                                                    size=int(display.page.scale*(data['title-size'] if 'title-size' in data else 18))),
		                                               alignment=flet_core_alignment.center))
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
		                                               alignment=flet_core_alignment.center))
		display.content.update()


	def on_button_wakeup(self, event: flet.ControlEvent) -> None:
		self.events.put_nowait({'topic': 'hal9000/command/brain/status', 'payload': 'awake'})

	def on_button_sleep(self, event: flet.ControlEvent) -> None:
		self.events.put_nowait({'topic': 'hal9000/command/brain/status', 'payload': 'asleep'})

	def on_control_up(self, event: flet.ControlEvent) -> None:
		self.events.put_nowait({'topic': 'device/input', 'payload': '{"source": {"type": "rotary", "name": "control"}, "event": {"delta": "+1"}}'})

	def on_control_down(self, event: flet.ControlEvent) -> None:
		self.events.put_nowait({'topic': 'device/input', 'payload': '{"source": {"type": "rotary", "name": "control"}, "event": {"delta": "-1"}}'})

	def on_control_select(self, event: flet.ControlEvent) -> None:
		self.events.put_nowait({'topic': 'device/input', 'payload': '{"source": {"type": "button", "name": "control"}, "event": {"status": "clicked"}}'})

	def on_volume_up(self, event: flet.ControlEvent) -> None:
		self.events.put_nowait({'topic': 'device/input', 'payload': '{"source": {"type": "rotary", "name": "volume"}, "event": {"delta": "+1"}}'})

	def on_volume_down(self, event: flet.ControlEvent) -> None:
		self.events.put_nowait({'topic': 'device/input', 'payload': '{"source": {"type": "rotary", "name": "volume"}, "event": {"delta": "-1"}}'})

	def on_volume_mute(self, event: flet.ControlEvent) -> None:
		self.events.put_nowait({'topic': 'device/input', 'payload': '{"source": {"type": "button", "name": "volume"}, "event": {"status": "clicked"}}'})


	def flet_on_disconnect(self, event: flet.ControlEvent) -> None:
		self.logger.info(f"[frontend:flet] terminating flet session '{event.page.session_id}'")
		if event.page.session_id in self.command_session_queues:
			command_session_queue = self.command_session_queues[event.page.session_id]
			del self.command_session_queues[event.page.session_id]
			command_session_queue.put_nowait(None)
			if len(self.command_session_queues) == 0:
				self.status = STATUS.OFFLINE
		

	async def flet(self, page: flet.Page) -> None:
		self.logger.info(f"[frontend:flet] starting new flet session '{page.session_id}'")
		page.on_disconnect = self.flet_on_disconnect
		page.title = "HAL9000"
		page.theme_mode = flet.ThemeMode.DARK
		page.scale = page.height / 1000
		page.padding = 0
		page.data = {}
		page.data['button_sleep'] = flet.Ref[flet.TextButton]()
		page.data['button_wakeup'] = flet.Ref[flet.TextButton]()
		display = flet.CircleAvatar(radius=int(page.scale*120), bgcolor='black')
		display.content = flet.canvas.Canvas(width=display.radius*2, height=display.radius*2)
		display.background_image_src = '/resources/images/display.jpg'
		display.data = {}
		display.data['idle_clock'] = flet.Ref[flet.canvas.Text]()
		display.data['animations'] = []
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
		                                                                 image_src="/resources/images/HAL9000.jpg", image_fit=flet.ImageFit.FILL),
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
		page.session.set('gui_animations_task', asyncio_create_task(self.run_gui_screen_animations(page, display)))
		page.session.set('idle_clock:synced', 'unknown')
		self.status = STATUS.ONLINE

