#!/usr/bin/env python3

from webserial import webserial
import sys
import time
import select
from datetime import datetime, timezone

menu = dict()
menu['0'] = ['Disconnect', None]
menu['1'] = ['Sync system time',      '["application/runtime",  {"time": {"epoch": %d}}]' % (int(datetime.now().timestamp() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))]
menu['2'] = ['Dump system settings',  '["application/settings", {"list": {}}]']
menu['3'] = ['Load system settings',  '["application/settings", {"load": {}}]']
menu['4'] = ['Save system settings',  '["application/settings", {"save": {}}]']
menu['5'] = ['Reset system settings', '["application/settings", {"reset":{}}]']
menu['6'] = ['Switch to screen "idle" (showing a clock)', '["gui/screen", {"idle":    {}}]']
menu['7'] = ['Switch to screen "splash" (error.jpg)',     '["gui/screen", {"splash":  {"filename": "error.jpg"}}]']
menu['9'] = ['Switch to screen "shutdown" (->halt MCU)',  '["gui/screen", {"shutdown":{}}]']
menu['+'] = ['Display: on',                '["device/display", {"backlight": "on"}]']
menu['-'] = ['Display: off',               '["device/display", {"backlight": "off"}]']
menu['r'] = ['Prepare shutdown: reboot',   '["application/runtime", {"shutdown": {"target": "reboot"}}]']
menu['p'] = ['Prepare shutdown: poweroff', '["application/runtime", {"shutdown": {"target": "poweroff"}}]']
menu['?'] = ['Application: query status',  '["application/runtime", {"status": ""}]']
menu['!'] = ['Application: send configuration EOF', '["", ""]']


def handler(self, line: str):
	if line is None or len(line) == 0:
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

