#!/usr/bin/python3

import io
import os
import os.path
import sys
import time
from datetime import datetime, timedelta

from configparser import ConfigParser
from PIL import Image

import board
import busio
import displayio
import digitalio
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle

from hal9000.peripherals.device import HAL9000_Device
from hal9000.peripherals.driver import HAL9000_Driver


class Device(HAL9000_Device):

	def __init__(self, name: str, Driver: HAL9000_Driver) -> None:
		HAL9000_Device.__init__(self, name, Driver)
		self.state = None
		self.overlay = None


	def configure(self, configuration: ConfigParser, section_name: str = None) -> None:
		HAL9000_Device.configure(self, configuration)
		self.driver = self.Driver(str(self))
		self.image_path = None
		if configuration:
			self.image_path = configuration.getstring('daemon:display', 'images-directory')
		else:
			self.image_path = sys.argv[1]
		self.overlay_volume = displayio.Group()
		self.overlay_volume.append(Circle(120,120,90,fill=None,outline=0xffffff,stroke=1))
		self.overlay_volume.append(Circle(120,120,115,fill=None,outline=0xffffff,stroke=1))

		self.state_init   = self.load_images(self.image_path + "/init/")
		self.state_wakeup = self.load_images(self.image_path + "/wakeup/")
		self.state_active = self.load_images(self.image_path + "/active/")
		self.state_wait   = self.load_images(self.image_path + "/wait/")
		self.state_sleep  = self.load_images(self.image_path + "/sleep/")
		self.state_splash  = self.load_image(self.image_path + "/splash/unknown.bmp")
		self.backlight = digitalio.DigitalInOut(board.D7)
		self.backlight.direction = digitalio.Direction.OUTPUT
		self.backlight.value = False


	def load_images(self, directory):
		frames = displayio.Group()
		for i in range(0,99):
			filename = "{}/{:02d}.bmp".format(directory, i)
			if os.path.isfile(filename):
				with open(filename, "rb") as file:
					image = displayio.TileGrid(displayio.OnDiskBitmap(file), pixel_shader=displayio.ColorConverter())
					layers = displayio.Group()
					layers.append(image)
					frames.append(layers)
		return frames


	def load_image(self, filename):
		with io.open(filename, 'rb') as file:
			buffer = io.BytesIO(file.read())
			image = Image.open(buffer).resize((240,240))
			buffer = io.BytesIO()
			image.save(buffer, format='BMP')
			buffer.seek(0)
			image = displayio.TileGrid(displayio.OnDiskBitmap(buffer), pixel_shader=displayio.ColorConverter())
			layers = displayio.Group()
			layers.append(image)
			frames = displayio.Group()
			frames.append(layers)
			return frames


	def on_init(self):
		self.state = self.state_init
		self.backlight.value = True


	def on_splash(self, filename):
		if filename is not None and len(filename) > 0 and os.path.isfile(filename):
			self.state_splash = self.load_image(filename)
			self.state = self.state_splash
		else:
			self.state_splash = self.load_image(self.image_path + "/splash/unknown.bmp")
			self.state = self.state_splash


	def on_wakeup(self):
		if self.state == self.state_sleep or self.state == self.state_init:
			self.backlight.value = True
			self.state = self.state_wakeup
		else:
			self.state = self.state_active


	def on_active(self):
		if self.state != self.state_wakeup:
			self.state = self.state_active


	def on_wait(self):
		if self.state == self.state_active:
			self.state = self.state_wait


	def on_sleep(self):
		self.state = self.state_sleep


	def on_volume_show(self):
		return self.on_overlay_show(self.overlay_volume)


	def on_volume_hide(self):
		return self.on_overlay_hide(self.overlay_volume)


	def on_overlay_show(self, overlay):
		if self.overlay == overlay:
			return
		if self.overlay is not None:
			self.on_overlay_hide(self.overlay)
		self.overlay = self.overlay_volume
		for i in range(0,len(self.state)):
			for j in range(0,len(self.overlay_volume)):
				self.state[i].append(self.overlay_volume[j])


	def on_overlay_hide(self, overlay):
		if self.overlay != overlay:
			return
		for i in range(0,len(self.state)):
			for j in range(0,len(self.overlay)):
				self.state[i].pop()
		self.overlay = None


	def do_loop(self, callback) -> bool: # TODO refactor as do_loop
		try:
			state = None
			overlay = None
			while self.state is None:
				time.sleep(0.1)
			wait_timeout = 0
			while True:
				refresh = False
				if state != self.state:
					refresh = True
					state = self.state
					if state == self.state_wakeup:
						self.backlight.value = True
					wait_timeout = 0
					if state == self.state_wait:
						wait_timeout = time.time() + 5
				if overlay != self.overlay:
					refresh = True
					overlay = self.overlay
				if state == self.state_active:
					refresh = True
				if refresh is True or self.overlay is not None:
					for frame in range(0,len(state)):
						self.driver.show(state[frame])
						self.driver.refresh()
						time.sleep(0.025)
					if state == self.state_wakeup:
						self.state = self.state_active
					if state == self.state_wait:
						if wait_timeout > 0 and time.time() > wait_timeout:
							self.state = self.state_sleep
							wait_timeout = 0
					if state == self.state_sleep:
						self.backlight.value = False
				time.sleep(0.050)
		except KeyboardInterrupt:
			displayio.release_displays()
		return False

