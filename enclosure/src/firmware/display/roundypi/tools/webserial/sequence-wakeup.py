#!/usr/bin/python3

from webserial import webserial

roundypi = webserial()
roundypi.connect()
roundypi.send('["display:sequence", {"action": "add", "sequence": [{"name": "wakeup", "timeout": 0}, {"name": "active", "timeout": 10}, {"name": "sleep", "timeout": 0}, {"name": "standby", "timeout": 0}]}]')
roundypi.run()

