#!/usr/bin/python3

import time
import board
import busio
import digitalio

from adafruit_mcp230xx.digital_inout import DigitalInOut
from adafruit_mcp230xx.mcp230xx import MCP230XX
from adafruit_mcp230xx.mcp23017 import MCP23017

from threading import Thread


class MCP230XX_Rotary(Thread):

	def __init__(self, mcp: MCP230XX, bank: str,
		     rot_sigA: int, rot_gnd: int, rot_sigB: int,
		     btn_gnd: int = 0, btn_sigX: int = 0,
		     pin_irq = None
		    ) -> None:
		Thread.__init__(self)
		self.mcp = mcp
		self.dio_rot_sigA = mcp.get_pin(self.bank_pin(bank, rot_sigA))
		self.dio_rot_GND = mcp.get_pin(self.bank_pin(bank, rot_gnd))
		self.dio_rot_sigB = mcp.get_pin(self.bank_pin(bank, rot_sigB))
		self.dio_btn_GND = mcp.get_pin(self.bank_pin(bank, btn_gnd))
		self.dio_btn_sigX = mcp.get_pin(self.bank_pin(bank, btn_sigX))
		self.dio_irq = digitalio.DigitalInOut(pin_irq)

		for pin in [self.dio_rot_GND, self.dio_btn_GND]:
			if pin is not None:
				pin.direction = digitalio.Direction.OUTPUT
				pin.value = False
		for pin in [self.dio_rot_sigA, self.dio_rot_sigB, self.dio_btn_sigX]:
			if pin is not None:
				pin.direction = digitalio.Direction.INPUT
				pin.pull = digitalio.Pull.UP
		if self.dio_irq is not None:
			if bank == 'A':
				mcp.interrupt_enable |= 0xFF00
			if bank == 'B':
				mcp.interrupt_enable |= 0x00FF
			mcp.interrupt_configuration = 0x0000
			mcp.io_control = 0x00
			mcp.clear_ints()

		self.rotary = dict()
		self.rotary['pos'] = 0
		self.rotary['min'] = 0
		self.rotary['max'] = 100
		self.rotary['state'] = dict()
		self.rotary['state']['data'] = 0x00
		self.rotary['state']['direction'] = 0
		self.button = dict()
		self.button['status'] = True

		self.thread = None


	def configure(self, rotary_pos: int = 0, rotary_min: int = 0, rotary_max: int = 100, button_status: bool = False) -> None:
		self.rotary['pos'] = rotary_pos
		self.rotary['min'] = rotary_min
		self.rotary['max'] = rotary_max
		self.button['status'] = button_status


	def do_loop(self, callback_rotary = None, callback_button = None):
		if self.dio_irq is None or self.dio_irq.value is False:
			if self.dio_irq is not None:
				self.mcp.clear_ints()
			if self.dio_rot_sigA is not None and self.dio_rot_sigB is not None:
				rotary_pos = self.calculate_rotary(self.dio_rot_sigA.value, self.dio_rot_sigB.value)
			if self.dio_btn_sigX is not None:
				button_status = not(self.dio_btn_sigX.value)
			if rotary_pos != self.position:
				self.position = rotary_pos
				if callback_rotary is not None:
					callback_rotary(self.position)
			if button_status != self.button['status']:
				self.button['status'] = button_status
				if callback_button is not None:
					callback_button(self.status)


	def loop(self, interval_ms: float = 1, callback_rotary = None, callback_button = None):
		while self.thread is not None:
			self.do_loop(callback_rotary, callback_button)
			if interval_ms > 0:
				time.sleep(interval_ms / 1000)


	def loop_start(self, interval_ms: float = 1, callback_rotary = None, callback_button = None) -> None:
		if self.thread is None:
			self.thread = Thread(target=self.loop, args=(interval_ms, callback_rotary, callback_button))
			self.thread.start()


	def loop_stop(self) -> None:
		if self.thread is not None:
			thread = self.thread
			self.thread = None
			thread.join()
		

	@property
	def position(self) -> int:
		return self.rotary['pos']

	
	@position.setter
	def position(self, position: int) -> None:
		if position >= self.rotary['min'] and position <= self.rotary['max']:
			self.rotary['pos'] = position


	@property
	def status(self) -> bool:
		return self.button['status']


	def calculate_rotary(self, valA: int, valB: int) -> int:
		rotary_state_data = ((valA&0x01) << 4) + ((valB&0x01) << 0)
		if rotary_state_data != self.rotary['state']['data']:
			rotary_pos = self.rotary['pos']
			if self.rotary['state']['data'] == 0x00:
				if rotary_state_data == 0x01:
					self.rotary['state']['direction'] = +1
				elif rotary_state_data == 0x10:
					self.rotary['state']['direction'] = -1
			elif self.rotary['state']['data'] == 0x01:
				if rotary_state_data == 0x11:
					self.rotary['state']['direction'] = +1
				elif rotary_state_data == 0x00:
					if self.rotary['state']['direction'] == -1:
						rotary_pos = rotary_pos - 1
			elif self.rotary['state']['data'] == 0x10:
				if rotary_state_data == 0x11:
					self.rotary['state']['direction'] = -1
				elif rotary_state_data == 0x00:
					if self.rotary['state']['direction'] == +1:
						rotary_pos = rotary_pos + 1
			else:
				if rotary_state_data == 0x01:
					self.rotary['state']['direction'] = -1
				elif rotary_state_data == 0x10:
					self.rotary['state']['direction'] = +1
				elif rotary_state_data == 0x00:
					if self.rotary['state']['direction'] == -1:
						rotary_pos = rotary_pos - 1
					elif self.rotary['state']['direction'] == +1:
						rotary_pos = rotary_pos + 1
			self.rotary['state']['data'] = rotary_state_data
			return rotary_pos
		return self.rotary['pos']

	def bank_pin(self, bank: str, pin: int) -> int:
		if bank == 'A':
			return self.bank_a_pin(pin)
		if bank == 'B':
			return self.bank_b_pin(pin)
		raise Exception("MCP230xx bank must be either 'A' or 'B'")

	def bank_a_pin(self, pin: int) -> int:
		return (pin + 0) & 0x07


	def bank_b_pin(self, pin: int) -> int:
		return (pin + 8) & 0x0f



def print_rotary(position: int):
	print("Rotary: pos={}".format(position))


def print_button(position: int):
	print("Button: status={}".format(position))


i2c = busio.I2C(board.SCL, board.SDA)
mcp = MCP23017(i2c, address=0x20)
mcp230xx_a = MCP230XX_Rotary(mcp, 'A', 5, 6, 7, 3, 4, board.D12)
mcp230xx_b = MCP230XX_Rotary(mcp, 'B', 0, 1, 2, 3, 4, board.D13)
mcp230xx_a.configure(5, 0, 10, False)
mcp230xx_b.configure(5, 0, 10, False)
mcp230xx_a.loop_start(2.5, print_rotary, print_button)
mcp230xx_b.loop_start(2.5, print_rotary, print_button)
while True:
#	mcp230xx_a.do_loop(print_rotary, print_button)
#	mcp230xx_b.do_loop(print_rotary, print_button)
	time.sleep(0.0025)

