#!/usr/bin/python3

import time
#import board
import busio
import digitalio

from adafruit_mcp230xx.digital_inout import DigitalInOut

from threading import Thread


class MCP230XX_Rotary():

	def __init__(self,
		     dio_rot_GND: DigitalInOut, dio_rot_sigA: DigitalInOut, dio_rot_sigB: DigitalInOut,
		     dio_btn_GND: DigitalInOut = None, dio_btn_sigX: DigitalInOut = None
		    ) -> None:
		Thread.__init__(self)
		self.dio_rot_GND = dio_rot_GND
		self.dio_rot_sigA = dio_rot_sigA
		self.dio_rot_sigB = dio_rot_sigB
		self.dio_btn_GND = dio_btn_GND
		self.dio_btn_sigX = dio_btn_sigX

		for pin in [self.dio_rot_GND, self.dio_btn_GND]:
			if pin is not None:
				pin.direction = digitalio.Direction.OUTPUT
				pin.value = False
		for pin in [self.dio_rot_sigA, self.dio_rot_sigB, self.dio_btn_sigX]:
			if pin is not None:
				pin.direction = digitalio.Direction.INPUT
				pin.pull = digitalio.Pull.UP

		self.thread = None

		self.rotary = ()
		self.rotary.pos = 0
		self.rotary.min = 0
		self.rotary.max = 100
		self.rotary.debounce_delay_ms = 0
		self.rotary.state = ()
		self.rotary.state.data = '00'
		self.rotary.state.direction = None
		self.rotary.state.timestamp_action = 0
		self.rotary.state.timestamp_debounced = 0

		self.button = ()
		self.button.pos = 0
		self.button.debounce_delay_ms = 0
		self.button.state = ()
		self.button.state.timestamp_action = 0
		self.button.state.timestamp_debounced = 0


	def configure(self, rotary_pos: int = 0, rotary_min: int = 0, rotary_max: int = 100, button_pos = 0, rotary_debounce_delay_ms: int = 0, button_debounce_delay_ms: int = 0) -> None:
		self.rotary.pos = rotary_pos
		self.rotary.min = rotary_min
		self.rotary.max = rotary_max
		self.rotary.state.debounce_delay = (float)rotary_debounce_delay_ms / 1000
		self.button.pos = button_pos
		self.button.state.debounce_delay = (float)button_debounce_delay_ms / 1000


	def loop(self, interval_ms: float = 10, callback_rotary = None, callback_button = None):
		if self.thread is None:
			self.thread = False
		while self.thread is not None:
			if self.thread is False:
				self.thread = None
			if self.dio_rot_sigA is not None and self.dio_rot_sigB is not None:
				rotary_pos = self.calculate_rotary(self.dio_rot_sigA.value(), self.dio_rot_sigB.value())
			if self.dio_btn_sigX is not None:
				button_pos = self.calculate_button(self.dio_btn_sigX.value())
			if rotary_pos != self.rotary.pos:
				self.rotary.pos = rotary_pos
				if callback_rotary is not None:
					callback_rotary(self.rotary.pos)
			if button_pos != self.button.pos:
				self.button.pos = button_pos
				if callback_button is not None:
					callback_button(self.button.pos)
			time.sleep(interval_ms / 1000)


	def loop_start(self, interval_ms: float = 10, callback_rotary = None, callback_button = None) -> None:
		if self.thread is None:
			self.thread = Thread(target=self.loop, interval_ms=interval_ms, callback_rotary=callback_rotary, callback_button=callback_button)
			self.thread.start()


	def loop_stop(self) -> None:
		if self.thread is not None:
			thread = self.thread
			self.thread = None
			thread.join()
		

	@property
	def rotary(self) -> int:
		return self.rotary.pos

	
	@rotary.setter
	def rotary(self, position: int) -> None:
		if position >= self.rotary.min and position <= self.rotary.max:
			self.rotary.pos = position


	@property
	def button(self) -> int:
		return self.button_pos


	def calculate_rotary(self, valA: int, valB: int) -> int:
		now = time.time()
		rotary_state_data = "{}{}".format(valA, valB)
		if rotary_state_data != self.rotary.state.data:
			if self.rotary.debounce_delay_ms > 0 and self.rotary.state.timestamp_debounced == 0:
				self.rotary.state.timestamp_debounced = now + (self.rotary.debounce_delay_ms / 1000)
			if now > self.rotary.state.timestamp_debounced:
				if self.rotary.debounce_delay_ms > 0:
					self.rotary.state.timestamp_debounced = 0
				rotary_pos = self.rotary.pos
				if self.rotary.state.data == "00": # Resting position
					if rotary_state_data == "01": # Turned right 1
						self.rotary.state.direction = "R"
					elif rotary_state_data == "10": # Turned left 1
						self.rotary.state.direction = "L"
				elif self.rotary.state.data == "01": # R1 or L3 position
					if rotary_state_data == "11": # Turned right 1
						self.rotary.state.direction = "R"
					elif rotary_state_data == "00": # Turned left 1
						if self.rotary.state.direction == "L":
							rotary_pos = rotary_pos - 1
				elif self.rotary.state.data == "10": # R3 or L1
					if rotary_state_data == "11": # Turned left 1
						self.rotary.state.direction = "L"
					elif rotary_state_data == "00": # Turned right 1
						if self.rotary.state.direction == "R":
							rotary_pos = rotary_pos + 1
				else: # self.rotary.state.data == "11"
					if rotary_state_data == "01": # Turned left 1
						self.rotary.state.direction = "L"
					elif rotary_state_data == "10": # Turned right 1
						self.rotary.state.direction = "R"
					elif rotary_state_data == "00": # Skipped an intermediate 01 or 10 state, but if we know direction then a turn is complete
						if self.rotary.state.direction == "L":
							rotary_pos = rotary_pos - 1
						elif self.rotary.state.direction == "R":
							rotary_pos = rotary_pos + 1
				self.rotary.state.timestamp_action = now
				self.rotary.state.data = rotary_state_data
				return rotary_pos
		return self.rotary.pos


	def calculate_button(self, btnX: int) -> int:
		now = time.time()
		if btnX != self.button.pos:
			if self.button.debounce_delay_ms > 0 and self.button.state.timestamp_debounced == 0:
				self.button.state.timestamp_debounced = now + (self.button.debounce_delay_ms / 1000)
			if now > self.button.state.timestamp_debounced:
				if self.button.debounce_delay_ms > 0:
					self.button.state.timestamp_debounced = 0
				self.button.state.timestamp_action = now
				return btnX
		return self.button.pos

	
# i2c = busio.I2C(board.SCL, board.SDA)
# mcp = MCP23017(i2c, address=0x20)
# pin_rot_sigA = mcp.get_pin(5)
# pin_rot_gnd = mcp.get_pin(6)
# pin_rot_sigB = mcp.get_pin(7)
# pin_btn_gnd = mcp.get_pin(3)
# pin_btn_sigX = mcp.get_pin(4)


def print_rotary(position: int):
	print("Rotary: pos={}".format(position))


def print_button(position: int):
	print("Button: pos={}".format(position))


pin_rot_sigA = DigitalInOut(0, None)
pin_rot_gnd = DigitalInOut(0, None)
pin_rot_sigB = DigitalInOut(0, None)
pin_btn_gnd = DigitalInOut(0, None)
pin_btn_sigX = DigitalInOut(0, None)

mcp230xx = MCP230XX_Rotary(pin_rot_gnd, pin_rot_sigA, pin_rot_sigB, pin_btn_gnd, pin_btn_sigX)
mcp230xx.configure(50, 0, 100, 50, 50)

#mcp230xx.loop_start(10, print_rotary, print_button)
#while True:
#	time.sleep(1)


while True:
	mcp230xx.loop(10, print_rotary, print_button)
	time.sleep(0.01)

