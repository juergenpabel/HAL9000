#!/usr/bin/python3

import os
import sys
import time
os.environ["BLINKA_FT232H"] = "1"

import asyncio
import board
import busio
import terminalio
import displayio
import digitalio
from digitalio import *
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle
from pyftdi.spi import SpiController
from PIL import Image,ImageDraw,ImageFont

from driver.waveshare_19192 import *
from driver.apa102 import *

class HAL9000:
	def __init__(self):
		leds = APA102(num_led=3)
		leds.set_pixel(0, 0, 0, 0)
		leds.set_pixel(1, 0, 0, 0)
		leds.set_pixel(2, 0, 0, 0)
		leds.show()

		spi = SpiController()
		spi.configure("ftdi://ftdi:ft232h/1")

		spi = busio.SPI(board.SCLK, board.MOSI, None)
		self.display = Waveshare_19192(displayio.FourWire(spi,baudrate=40000000,command=board.D5,chip_select=board.D4,reset=board.D6),width=240,height=240,backlight_pin=board.D7,auto_refresh=False)
		self.state = None

		self.state_init = displayio.Group(max_size=10)
		for i in range(0,10):
			image_file = open(sys.argv[1] + "/init/0" + str(i) + ".bmp", "rb")
			image_data = displayio.OnDiskBitmap(image_file)
			image_sprite = displayio.TileGrid(image_data, pixel_shader=displayio.ColorConverter())
			image_group = displayio.Group(max_size=1)
			image_group.append(image_sprite)
			self.state_init.append(image_group)

		self.state_wakeup = displayio.Group(max_size=10)
		for i in range(0,10):
			image_file = open(sys.argv[1] + "/wakeup/0" + str(i) + ".bmp", "rb")
			image_data = displayio.OnDiskBitmap(image_file)
			image_sprite = displayio.TileGrid(image_data, pixel_shader=displayio.ColorConverter())
			image_group = displayio.Group(max_size=1)
			image_group.append(image_sprite)
			self.state_wakeup.append(image_group)

		self.state_active = displayio.Group(max_size=10)
		for i in range(0,10):
			image_file = open(sys.argv[1] + "/active/0" + str(i) + ".bmp", "rb")
			image_data = displayio.OnDiskBitmap(image_file)
			image_sprite = displayio.TileGrid(image_data, pixel_shader=displayio.ColorConverter())
			image_group = displayio.Group(max_size=1)
			image_group.append(image_sprite)
			self.state_active.append(image_group)

		self.state_wait = displayio.Group(max_size=1)
		for i in range(0,1):
			image_file = open(sys.argv[1] + "/wait/0" + str(i) + ".bmp", "rb")
			image_data = displayio.OnDiskBitmap(image_file)
			image_sprite = displayio.TileGrid(image_data, pixel_shader=displayio.ColorConverter())
			image_group = displayio.Group(max_size=1)
			image_group.append(image_sprite)
			self.state_wait.append(image_group)

		self.state_sleep = displayio.Group(max_size=10)
		for i in range(0,10):
			image_file = open(sys.argv[1] + "/sleep/0" + str(i) + ".bmp", "rb")
			image_data = displayio.OnDiskBitmap(image_file)
			image_sprite = displayio.TileGrid(image_data, pixel_shader=displayio.ColorConverter())
			image_group = displayio.Group(max_size=1)
			image_group.append(image_sprite)
			self.state_sleep.append(image_group)

		self.display.brightness = 1
		self.display.show(self.state_init[0])
		self.display.refresh()
		self.state = self.state_sleep

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

	def loop(self):
		try:
			state = self.state
			wait_timeout = 0
			while True:
				changed = False
				if state != self.state:
					changed = True
					state = self.state
					wait_timeout = 0
					if state == self.state_wait:
						wait_timeout = time.time() + 5
				if changed is True or state == self.state_active or state == self.state_wait:
					for i in range(0,len(state)):
						self.display.show(state[i])
						self.display.refresh()
					if state == self.state_wakeup:
						self.state = self.state_active
					if state == self.state_wait:
						if wait_timeout > 0 and time.time() > wait_timeout:
							self.state = self.state_sleep
							wait_timeout = 0
				time.sleep(0.05)
		except KeyboardInterrupt:
			displayio.release_displays()


