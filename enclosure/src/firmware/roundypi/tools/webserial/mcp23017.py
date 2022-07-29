#!/usr/bin/python3

from webserial import webserial
import sys
import time
import select
from datetime import datetime, timezone

def handler(self, line: str):
	pass

roundypi = webserial()
roundypi.connect()
roundypi.send('["mcp23017:setup", {"mcp23017": {"i2c-address": "32", "pin-sda": 0, "pin-scl": 1}}]')
roundypi.send('["mcp23017:setup", {"inputs": {"control:button": {"pin": "A2", "trigger": "high"}}}]')
roundypi.send('["mcp23017:setup", {"inputs": {"control:rotary": {"pin": "A1"}}}]')
roundypi.send('["mcp23017:setup", {"inputs": {"control:rotary": {"pin": "A0"}}}]')
roundypi.send('["mcp23017:setup", {"inputs": {"volume:button":  {"pin": "A7", "trigger": "high"}}}]')
roundypi.send('["mcp23017:setup", {"inputs": {"volume:rotary":  {"pin": "A6"}}}]')
roundypi.send('["mcp23017:setup", {"inputs": {"volume:rotary":  {"pin": "A5"}}}]')
roundypi.send('["mcp23017:loop",  {"core": 2}]')
roundypi.run(handler)

