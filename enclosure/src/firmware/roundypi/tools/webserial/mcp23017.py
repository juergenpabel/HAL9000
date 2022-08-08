#!/usr/bin/python3

from webserial import webserial
import sys
import time
import select
import json
from datetime import datetime, timezone

roundypi = None

def handler(self, line: str):
	if line.startswith('["device/event"'):
		data = json.loads(line)[1]
		if data["device"]["name"] == "volume":
			self.volume += int(data["event"]["delta"])
			roundypi.send('["system/settings", {"set": {"key": "audio/volume", "value": "%d"}}]' % (self.volume))
			roundypi.send('["gui/overlay", {"show": "volume"}]')
		if data["device"]["name"] == "volume:mute":
			roundypi.send('["gui/overlay", {"hide": "volume"}]')

roundypi = webserial()
roundypi.volume = 50
roundypi.connect()
roundypi.send('["device/mcp23X17", {"init": {"i2c-address": 32, "pin-sda": 0, "pin-scl": 1}}]')
roundypi.send('["device/mcp23X17", {"config": {"device": {"name": "volume:mute",    "type": "toggle", "inputs": [{"pin": "A7", "label": "sigX"}], "actions": {"true": "on", "false": "off"}}}}]')
roundypi.send('["device/mcp23X17", {"config": {"device": {"name": "volume",         "type": "rotary", "inputs": [{"pin": "A6", "label": "sigA"},{"pin": "A5", "label": "sigB"}]}}}]')
roundypi.send('["device/mcp23X17", {"config": {"device": {"name": "control:select", "type": "button", "inputs": [{"pin": "A2", "label": "sigX"}], "actions": {}}}}]')
roundypi.send('["device/mcp23X17", {"config": {"device": {"name": "control",        "type": "rotary", "inputs": [{"pin": "A1", "label": "sigA"},{"pin": "A0", "label": "sigB"}]}}}]')
#roundypi.send('["device/mcp23X17", {"config": {"device": {"name": "rfid",           "type": "switch", "inputs": [{"pin": "B0", "label": "sigX"}], "actions": {}}}}]')
#roundypi.send('["device/mcp23X17", {"config": {"device": {"name": "motion",         "type": "switch", "inputs": [{"pin": "B1", "label": "sigX"}], "actions": {}}}}]')
roundypi.send('["device/mcp23X17",  {"start": true}]')
roundypi.run(handler)

