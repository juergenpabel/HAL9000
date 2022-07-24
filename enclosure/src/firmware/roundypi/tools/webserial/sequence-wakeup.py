#!/usr/bin/python3

from webserial import webserial

def handler(self, line: str):
	if line.strip('"') == "system:time":
		self.send('["system:time",{"epoch-seconds": '+str(int(time.time() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds))+'}]')

roundypi = webserial()
roundypi.connect()
roundypi.send('["system:time", {"interval": 60}]')
roundypi.send('["gui:sequence", {"action": "add", "sequence": [{"name": "wakeup", "timeout": 0}, {"name": "active", "timeout": 10}, {"name": "sleep", "timeout": 0}, {"name": "standby", "timeout": 0}]}]')
roundypi.run(handler)

