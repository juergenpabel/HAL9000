# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Juergen Pabel
#
# SPDX-License-Identifier: MIT
"""
`waveshare_19192`
================================================================================

displayio driver for GC9A01 based Waveshare 1.28 inch TFT LCD display (sku 19192)


* Author(s): Juergen Pabel

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
"""

# imports

__version__ = "1.0.0"
__repo__ = "https://github.com/tylercrumpton/CircuitPython_Waveshare_19192.git"
import board
import busio

from displayio import Display, FourWire
from configparser import ConfigParser

from hal9000.driver import HAL9000_Driver as HAL9000


_INIT_SEQUENCE = bytearray(
	b"\xEF\x00"
	b"\xEB\x01\x14"
	b"\xFE\x00"
	b"\xEF\x00"
	b"\xEB\x01\x14"
	b"\x84\x01\x40"
	b"\x85\x01\xFF"
	b"\x86\x01\xFF"
	b"\x87\x01\xFF"
	b"\x88\x01\x0A"
	b"\x89\x01\x21"
	b"\x8A\x01\x00"
	b"\x8B\x01\x80"
	b"\x8C\x01\x01"
	b"\x8D\x01\x01"
	b"\x8E\x01\xFF"
	b"\x8F\x01\xFF"
	b"\xB6\x02\x00\x20"
	b"\x36\x01\x08"
	b"\x3A\x01\x05"
	b"\x90\x04\x08\x08\x08\x08"
	b"\xBD\x01\x06"
	b"\xBC\x01\x00"
	b"\xFF\x03\x60\x01\x04"
	b"\xC3\x01\x13"
	b"\xC4\x01\x13"
	b"\xC9\x01\x22"
	b"\xBE\x01\x11"
	b"\xE1\x02\x10\x0E"
	b"\xDF\x03\x21\x0C\x02"
	b"\xF0\x06\x45\x09\x08\x08\x26\x2A"
	b"\xF1\x06\x43\x70\x72\x36\x37\x6F"
	b"\xF2\x06\x45\x09\x08\x08\x26\x2A"
	b"\xF3\x06\x43\x70\x72\x36\x37\x6F"
	b"\xED\x02\x1B\x0B"
	b"\xAE\x01\x77"
	b"\xCD\x01\x63"
	b"\x70\x09\x07\x07\x04\x0E\x0F\x09\x07\x08\x03"
	b"\xE8\x01\x34"
	b"\x62\x0c\x18\x0D\x71\xED\x70\x70\x18\x0F\x71\xEF\x70\x70"
	b"\x63\x0c\x18\x11\x71\xF1\x70\x70\x18\x13\x71\xF3\x70\x70"
	b"\x64\x07\x28\x29\xF1\x01\xF1\x00\x07"
	b"\x66\x0a\x3C\x00\xCD\x67\x45\x45\x10\x00\x00\x00"
	b"\x67\x0a\x00\x3C\x00\x00\x00\x01\x54\x10\x32\x98"
	b"\x74\x07\x10\x85\x80\x00\x00\x4E\x00"
	b"\x98\x02\x3E\x07"
	b"\x35\x00"
	b"\x21\x00"
	b"\x11\x80\x78"
	b"\x29\x80\x14"
)


class Driver(HAL9000, Display):

	def __init__(self, name: str):
		HAL9000.__init__(self, name)
		Display.__init__(self, FourWire(busio.SPI(None),baudrate=320000000,command=board.D5,chip_select=board.D4,reset=board.D6), _INIT_SEQUENCE, width=240,height=240,backlight_pin=None,auto_refresh=False)
		self.config = dict()


	def configure(self, configuration: ConfigParser):
		HAL9000.configure(self, configuration)


	def _release(self):
	    pass

