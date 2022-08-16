#!/usr/bin/python3

from webserial import webserial
import sys
import time
import select
import json
from datetime import datetime, timezone

def handler(self, line: str):
	if line.startswith('['):
		if json.loads(line)[0] == "system/time":
			self.send('["system/time",{"sync":{"epoch":'+str(int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))+'}}]')

roundypi = webserial()
roundypi.connect()
roundypi.send('["system/time", {"config":{"interval":60}}]')
roundypi.run(handler)

