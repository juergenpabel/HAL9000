#!/usr/bin/python3

from webserial import webserial
import sys
import time
import select
from datetime import datetime, timezone

def handler(self, line: str):
	if line.strip('"') == "system:time":
		self.send('["system:time",{"epoch-seconds": '+str(int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))+'}]')

roundypi = webserial()
roundypi.connect()
roundypi.send('["system:time", {"interval": 60}]')
roundypi.run(handler)

