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
roundypi.send('["mcp23X17:setup", {"mcp23X17": {"i2c-address": "32", "pin-sda": 0, "pin-scl": 1}}]')
roundypi.send('["mcp23X17:setup", {"device": {"name": "volume:mute",    "type": "toggle", "inputs": [{"pin": "A7", "label": "sigX"}], "actions": {"true": "on", "false": "off"}}}]')
roundypi.send('["mcp23X17:setup", {"device": {"name": "volume",         "type": "rotary", "inputs": [{"pin": "A6", "label": "sigA"},{"pin": "A5", "label": "sigB"}]}}]')
roundypi.send('["mcp23X17:setup", {"device": {"name": "control:select", "type": "button", "inputs": [{"pin": "A2", "label": "sigX"}], "actions": {}}}]')
roundypi.send('["mcp23X17:setup", {"device": {"name": "control",        "type": "rotary", "inputs": [{"pin": "A1", "label": "sigA"},{"pin": "A0", "label": "sigB"}]}}]')
roundypi.send('["mcp23X17:loop",  {"delay": 0}]')
roundypi.run(handler)

