#!/usr/bin/python3

import json
import time
from datetime import datetime, timezone
from webserial import webserial

def handler(self, line: str):
	if line.startswith('['):
		if json.loads(line)[0] == "system/time#sync":
			self.send('["system/time",{"sync": {"epoch-seconds": '+str(int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))+'}}]')

roundypi = webserial()
roundypi.connect()
roundypi.send('["system/time", {"config": {"interval": 60}}]')
roundypi.send('["gui/screen",  {"sequence": {"queue": [{"name": "wakeup", "timeout": 0}, {"name": "active", "timeout": 10}, {"name": "sleep", "timeout": 0}, {"name": "standby", "timeout": 0}]}}]')
roundypi.run(handler)

