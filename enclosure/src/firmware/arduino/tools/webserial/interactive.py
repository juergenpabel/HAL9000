#!/usr/bin/python3

from webserial import webserial
import sys
import time
import select
from datetime import datetime, timezone

menu = dict()
menu['1'] = ['Wakeup sequence', '["gui/screen", {"sequence" :{"queue": [{"name": "wakeup", "timeout": 0}, {"name": "active", "timeout": 10}, {"name": "sleep", "timeout": 0}]}}]']
menu['2'] = ['Splash JPG (timeout=3)', '["gui/screen", {"splash": {"filename": "error.jpg", "timeout": 3}}]']


def handler(self, line: str):
	if len(line):
		if line.strip('"') == "system/time":
			self.send('["system/time", "sync":{"epoch":'+str(int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))+'}}]')
	else:
		if select.select([sys.stdin, ], [], [], 0.0)[0]:
			choice = sys.stdin.read(1)
			if choice in menu:
				self.send(menu[choice][1])
			

roundypi = webserial()
roundypi.connect()
print('COMMANDS')
print('========')
for key in menu.keys():
	print("{}: {}".format(key, menu[key][0]))
	
roundypi.send('["system/time", {"interval": 60}]')
roundypi.run(handler)

