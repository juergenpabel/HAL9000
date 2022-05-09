#!/usr/bin/python3

import time
import board
import busio
import digitalio

from adafruit_mcp230xx.digital_inout import DigitalInOut
from adafruit_mcp230xx.mcp23017 import MCP23017

from threading import Thread


class MCP230XX_Rotary():

	def __init__(self,
		     dio_rot_GND: DigitalInOut, dio_rot_sigA: DigitalInOut, dio_rot_sigB: DigitalInOut,
		     dio_btn_GND: DigitalInOut = None, dio_btn_sigX: DigitalInOut = None,
		     dio_irq: DigitalInOut = None
		    ) -> None:
		Thread.__init__(self)
		self.dio_rot_GND = dio_rot_GND
		self.dio_rot_sigA = dio_rot_sigA
		self.dio_rot_sigB = dio_rot_sigB
		self.dio_btn_GND = dio_btn_GND
		self.dio_btn_sigX = dio_btn_sigX
		self.dio_irq = dio_irq

		for pin in [self.dio_rot_GND, self.dio_btn_GND]:
			if pin is not None:
				pin.direction = digitalio.Direction.OUTPUT
				pin.value = False
		for pin in [self.dio_rot_sigA, self.dio_rot_sigB, self.dio_btn_sigX]:
			if pin is not None:
				pin.direction = digitalio.Direction.INPUT
				pin.pull = digitalio.Pull.UP

		self.thread = None

		self.rotary = dict()
		self.rotary['pos'] = 0
		self.rotary['min'] = 0
		self.rotary['max'] = 100
		self.rotary['state'] = dict()
		self.rotary['state']['data'] = '00'
		self.rotary['state']['direction'] = None

		self.button = dict()
		self.button['status'] = True


	def configure(self, rotary_pos: int = 0, rotary_min: int = 0, rotary_max: int = 100, button_status: bool = False) -> None:
		self.rotary['pos'] = rotary_pos
		self.rotary['min'] = rotary_min
		self.rotary['max'] = rotary_max
		self.button['status'] = button_status


	def do_loop(self, callback_rotary = None, callback_button = None):
		if self.dio_irq is None or self.dio_irq.value is False:
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


	def loop(self, interval_ms: int = 1, callback_rotary = None, callback_button = None):
		if self.thread is None:
			self.thread = False
		while self.thread is not None:
			if self.thread is False:
				self.thread = None
			self.do_loop(callback_rotary, callback_button)
			if self.thread is not None:
				if interval_ms > 0:
					time.sleep(float(interval_ms) / 1000)


	def loop_start(self, interval_ms: int = 10, callback_rotary = None, callback_button = None) -> None:
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
		rotary_state_data = "{:d}{:d}".format(valA, valB)
		if rotary_state_data != self.rotary['state']['data']:
			rotary_pos = self.rotary['pos']
			if self.rotary['state']['data'] == "00": # Resting position
				if rotary_state_data == "01": # Turned right 1
					self.rotary['state']['direction'] = "R"
				elif rotary_state_data == "10": # Turned left 1
					self.rotary['state']['direction'] = "L"
			elif self.rotary['state']['data'] == "01": # R1 or L3 position
				if rotary_state_data == "11": # Turned right 1
					self.rotary['state']['direction'] = "R"
				elif rotary_state_data == "00": # Turned left 1
					if self.rotary['state']['direction'] == "L":
						rotary_pos = rotary_pos - 1
			elif self.rotary['state']['data'] == "10": # R3 or L1
				if rotary_state_data == "11": # Turned left 1
					self.rotary['state']['direction'] = "L"
				elif rotary_state_data == "00": # Turned right 1
					if self.rotary['state']['direction'] == "R":
						rotary_pos = rotary_pos + 1
			else: # self.rotary['state']['data'] == "11"
				if rotary_state_data == "01": # Turned left 1
					self.rotary['state']['direction'] = "L"
				elif rotary_state_data == "10": # Turned right 1
					self.rotary['state']['direction'] = "R"
				elif rotary_state_data == "00": # Skipped an intermediate 01 or 10 state, but if we know direction then a turn is complete
					if self.rotary['state']['direction'] == "L":
						rotary_pos = rotary_pos - 1
					elif self.rotary['state']['direction'] == "R":
						rotary_pos = rotary_pos + 1
			self.rotary['state']['data'] = rotary_state_data
			return rotary_pos
		return self.rotary['pos']



def print_rotary(position: int):
	print("Rotary: pos={}".format(position))


def print_button(position: int):
	print("Button: status={}".format(position))


i2c = busio.I2C(board.SCL, board.SDA)
mcp = MCP23017(i2c, address=0x20)

pin_rot_sigA = mcp.get_pin(5)
pin_rot_gnd = mcp.get_pin(6)
pin_rot_sigB = mcp.get_pin(7)
pin_btn_gnd = mcp.get_pin(3)
pin_btn_sigX = mcp.get_pin(4)
mcp230xx_a = MCP230XX_Rotary(pin_rot_gnd, pin_rot_sigA, pin_rot_sigB, pin_btn_gnd, pin_btn_sigX)
mcp230xx_a.configure(50, 0, 100, False)

pin_rot_sigA = mcp.get_pin(10)
pin_rot_gnd = mcp.get_pin(9)
pin_rot_sigB = mcp.get_pin(8)
pin_btn_gnd = mcp.get_pin(12)
pin_btn_sigX = mcp.get_pin(11)
mcp230xx_b = MCP230XX_Rotary(pin_rot_gnd, pin_rot_sigA, pin_rot_sigB, pin_btn_gnd, pin_btn_sigX)
mcp230xx_b.configure(50, 0, 100, False)

irq_a = digitalio.DigitalInOut(board.D12)
irq_b = digitalio.DigitalInOut(board.D13)
while True:
	if not irq_a.value:
		mcp.clear_inta()
		mcp230xx_a.do_loop(print_rotary, print_button)
	if not irq_b.value:
		mcp.clear_intb()
		mcp230xx_b.do_loop(print_rotary, print_button)
	time.sleep(0.001)

