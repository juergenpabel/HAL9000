#!/usr/bin/python3

from webserial import webserial
import sys
import time
import select
from datetime import datetime, timezone

menu = dict()
menu['0'] = ['Disconnect', None]
menu['1'] = ['Dump system runtime',   '["system/runtime",  {"list": {}}]']
menu['2'] = ['Dump system settings',  '["system/settings", {"list": {}}]']
menu['3'] = ['Load system settings',  '["system/settings", {"load": {}}]']
menu['4'] = ['Save system settings',  '["system/settings", {"save": {}}]']
menu['5'] = ['Reset system settings', '["system/settings", {"reset":{}}]']
menu['6'] = ['Switch to screen "idle" (showing a clock)', '["gui/screen", {"idle":    {}}]']
menu['7'] = ['Switch to screen "splash" (error.jpg)',     '["gui/screen", {"splash":  {"filename": "error.jpg"}}]']
menu['9'] = ['Switch to screen "shutdown" (->halt MCU)',  '["gui/screen", {"shutdown":{}}]']
menu['h'] = ['Switch to screen "hal9000" ("wakeup")',     '["gui/screen", {"hal9000": {"queue": "replace", "sequence": {"name": "wakeup", "loop": "false"}}}]']
menu['a'] = ['Switch to screen "hal9000" ("active")',     '["gui/screen", {"hal9000": {"queue": "append",  "sequence": {"name": "active", "loop": "true"}}}]']
menu['l'] = ['Switch to screen "hal9000" ("sleep")',      '["gui/screen", {"hal9000": {"queue": "replace", "sequence": {"name": "sleep",  "loop": "false"}}}]']
menu['+'] = ['Display: on',                               '["device/display", {"backlight": "on"}]']
menu['-'] = ['Display: off',                              '["device/display", {"backlight": "off"}]']
menu['*'] = ['Condition: awake',                          '["system/runtime", {"condition": "awake"}]']
menu['#'] = ['Condition: asleep',                         '["system/runtime", {"condition": "asleep"}]']
menu['r'] = ['Prepare shutdown: reboot',                  '["system/app", {"shutdown": {"target": "reboot"}}]']
menu['p'] = ['Prepare shutdown: poweroff',                '["system/app", {"shutdown": {"target": "poweroff"}}]']


def handler(self, line: str):
	if line is not None and len(line) > 0:
		if line.strip() == '["system/time", {"sync":{"format":"epoch"}}]':
			self.send('["system/time", {"sync":{"epoch":'+str(int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))+'}}]')
	else:
		if select.select([sys.stdin, ], [], [], 0.0)[0]:
			choice = sys.stdin.read(1)
			if choice in menu:
				if menu[choice][1] is None:
					print("Disconnecting")
					sys.exit(0)
				self.send(menu[choice][1])
			if choice == 'h':
				self.send(menu['a'][1])

hal9000 = webserial(True, True)
hal9000.connect()
print('COMMANDS')
print('========')
for key in menu.keys():
	print("{}: {}".format(key, menu[key][0]))
hal9000.run(handler)

