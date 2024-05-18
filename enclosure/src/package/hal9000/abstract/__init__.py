#!/usr/bin/python3


class HAL9000_Abstract:

	def __init__(self, name: str) -> None:
		self._name = name


	def __str__(self):
		return self._name

