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
roundypi.send('["mcp23017:begin", {}]')
roundypi.send('["mcp23017:config", { "inputs": { "volume-select": "A7", "control-select": "A0"}}]')
roundypi.run(handler)

