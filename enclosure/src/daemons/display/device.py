#!/usr/bin/python3

import os
import os.path
import sys
import time
os.environ["BLINKA_FT232H"] = "1"

from configparser import ConfigParser
import board
import busio
import displayio
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle

from driver import Driver as Waveshare_19192
from hal9000.device import HAL9000_Device as HAL9000

class Device(HAL9000):

	def __init__(self) -> None:
		HAL9000.__init__(self, 'display')
		spi = busio.SPI(None)
		self.display = Waveshare_19192(displayio.FourWire(spi,baudrate=320000000,command=board.D5,chip_select=board.D4,reset=board.D6),width=240,height=240,backlight_pin=None,auto_refresh=False)
		self.state = None
		self.overlay = None


	def configure(self, config: ConfigParser) -> None:
		images = None
		if config:
			images = config['display']['images']
		else:
			images = sys.argv[1]
		self.overlay_volume = displayio.Group()
		self.overlay_volume.append(Circle(120,120,90,fill=None,outline=0xffffff,stroke=1))
		self.overlay_volume.append(Circle(120,120,115,fill=None,outline=0xffffff,stroke=1))

		self.state_init   = self.load_images(images + "/init/")
		self.state_wakeup = self.load_images(images + "/wakeup/")
		self.state_active = self.load_images(images + "/active/")
		self.state_wait   = self.load_images(images + "/wait/")
		self.state_sleep  = self.load_images(images + "/sleep/")
		self.display.brightness = 0


	def load_images(self, path):
		frames = displayio.Group()
		for i in range(0,99):
			filename = "{}/{:02d}.bmp".format(path, i)
			if os.path.isfile(filename):
				with open(filename, "rb") as file:
					image = displayio.TileGrid(displayio.OnDiskBitmap(file), pixel_shader=displayio.ColorConverter())
					layers = displayio.Group()
					layers.append(image)
					frames.append(layers)
		return frames


	def on_init(self):
		self.state = self.state_init


	def on_wakeup(self):
		if self.state == self.state_sleep or self.state == self.state_init:
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


	def do_loop(self) -> bool: # TODO refactor as do_loop
		try:
			state = None
			while self.state is None:
				time.sleep(0.1)
			self.display.brightness = 1
			wait_timeout = 0
			while True:
				changed = False
				if state != self.state:
					changed = True
					state = self.state
					if state == self.state_wakeup:
						self.display.brightness = 1
					wait_timeout = 0
					if state == self.state_wait:
						wait_timeout = time.time() + 5
				if changed is True or state == self.state_active or state == self.state_wait:
					for frame in range(0,len(state)):
						self.display.show(state[frame])
						self.display.refresh()
						time.sleep(0.05)
					if state == self.state_wakeup:
						self.state = self.state_active
					if state == self.state_wait:
						if wait_timeout > 0 and time.time() > wait_timeout:
							self.state = self.state_sleep
							wait_timeout = 0
					if state == self.state_init:
						self.state = self.state_wait
					if state == self.state_sleep:
						self.display.brightness = 0
				time.sleep(0.1)
		except KeyboardInterrupt:
			displayio.release_displays()
		return False


