#!/usr/bin/python3

from webserial import webserial
import sys
import time
import select
import json
from datetime import datetime, timezone

hal9000 = None

def handler(self, line: str):
	if line is not None:
		if line == '["application/runtime", "configuring"]':
			hal9000.send('["device/mcp23X17", {"init": {"i2c-bus": 0, "i2c-address": 32}}]')
			hal9000.send('["device/mcp23X17", {"config": {"device": {"type": "rotary", "name": "control", "inputs": [{"pin": "A1", "label": "sigA"},{"pin": "A0", "label": "sigB"}]}}}]')
			hal9000.send('["device/mcp23X17", {"config": {"device": {"type": "rotary", "name": "volume",  "inputs": [{"pin": "A6", "label": "sigA"},{"pin": "A5", "label": "sigB"}]}}}]')
			hal9000.send('["device/mcp23X17", {"config": {"device": {"type": "button", "name": "control", "inputs": [{"pin": "A2", "label": "sigX"}], "events": {}}}}]')
			hal9000.send('["device/mcp23X17", {"config": {"device": {"type": "toggle", "name": "volume",  "inputs": [{"pin": "A7", "label": "sigX"}], "events": {"high": "on", "low": "off"}}}}]')
			hal9000.send('["device/mcp23X17", {"config": {"device": {"type": "switch", "name": "motion",  "inputs": [{"pin": "B1", "label": "sigX"}], "events": {}}}}]')
			hal9000.send('["device/mcp23X17", {"start": true}]')
			hal9000.send('["", ""]')
		if line.startswith('["device/event"'):
			data = json.loads(line)[1]
			if data["device"]["name"] == "volume":
				if data["device"]["type"] == "rotary":
					self.volume += int(data["event"]["delta"])
					hal9000.send('["gui/overlay", {"overlay": {"volume": "show", "data": {"level": "%s", "mute": "false"}}}]' % self.volume)
				if data["device"]["type"] == "toggle":
					hal9000.send('["gui/overlay", {"overlay": {}}]')

hal9000 = webserial(True, True)
hal9000.volume = 50
hal9000.connect()
hal9000.run(handler)

