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
			if data["device"]["type"] == "rotary":
				self.volume += int(data["event"]["delta"])
				roundypi.send('["gui/overlay", {"overlay": {"volume": "show", "data": {"level": "%s", "mute": "false"}}}]' % self.volume)
			if data["device"]["type"] == "toggle":
				roundypi.send('["gui/overlay", {"overlay": {}}]')

roundypi = webserial()
roundypi.volume = 50
roundypi.connect()
roundypi.send('["device/mcp23X17", {"init": {"i2c-address": 32, "pin-sda": 32, "pin-scl": 33}}]')
roundypi.send('["device/mcp23X17", {"config": {"device": {"type": "rotary", "name": "control", "inputs": [{"pin": "A1", "label": "sigA"},{"pin": "A0", "label": "sigB"}]}}}]')
roundypi.send('["device/mcp23X17", {"config": {"device": {"type": "rotary", "name": "volume",  "inputs": [{"pin": "A6", "label": "sigA"},{"pin": "A5", "label": "sigB"}]}}}]')
roundypi.send('["device/mcp23X17", {"config": {"device": {"type": "button", "name": "control", "inputs": [{"pin": "A2", "label": "sigX"}], "events": {}}}}]')
roundypi.send('["device/mcp23X17", {"config": {"device": {"type": "toggle", "name": "volume",  "inputs": [{"pin": "A7", "label": "sigX"}], "events": {"high": "on", "low": "off"}}}}]')
roundypi.send('["device/mcp23X17", {"config": {"device": {"type": "switch", "name": "motion",  "inputs": [{"pin": "B1", "label": "sigX"}], "events": {}}}}]')
roundypi.send('["device/mcp23X17", {"start": true}]')
roundypi.run(handler)

