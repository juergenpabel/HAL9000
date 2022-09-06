#!/usr/bin/python3

from webserial import webserial
import sys
import time
import select
from datetime import datetime, timezone

menu = dict()
menu['0'] = ['Reset system', '["system/reset", {}]']
menu['1'] = ['Dump system runtime',   '["system/runtime",  {"list": {}}]']
menu['2'] = ['Dump system settings',  '["system/settings", {"list": {}}]']
menu['3'] = ['Load system settings',  '["system/settings", {"load": {}}]']
menu['4'] = ['Save system settings',  '["system/settings", {"save": {}}]']
menu['5'] = ['Reset system settings', '["system/settings", {"reset":{}}]']
menu['6'] = ['Switch to screen "hal9000" (animation)',    '["gui/screen", {"screen": {"hal9000": "show", "data": {"frames": "active"}}}]']
menu['7'] = ['Switch to screen "splash" (error.jpg)',     '["gui/screen", {"screen": {"splash":  "show", "data": {"filename": "error.jpg"}}}]']
menu['8'] = ['Switch to screen "idle" (showing a clock)', '["gui/screen", {"screen": {"idle":    "show"}}]']
menu['9'] = ['Switch to screen "shutdown" (->halt MCU)',  '["gui/screen", {"screen": {"shutdown":"show"}}]']


def handler(self, line: str):
	if len(line):
		if line.strip() == '["system/time",{"sync":{"format":"epoch"}}]':
			self.send('["system/time", {"sync":{"epoch":'+str(int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))+'}}]')
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
	
roundypi.send('["system/time", {"config": {"interval": 60}}]')
roundypi.run(handler)

