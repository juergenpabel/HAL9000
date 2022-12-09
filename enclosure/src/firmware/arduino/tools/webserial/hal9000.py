#!/usr/bin/python3

from webserial import webserial
import json

hal9000_commands = None


def handler(host: webserial, line: str):
	if line is not None:
		topic, body = json.loads(line)
		if topic in hal9000_commands:
			hal9000_commands[topic](host, topic, body)


def system_application(host: webserial, topic: str, request):
	response = [topic+"#status", host.status]
	host.send(json.dumps(response))
	host.status = "online"


def system_runtime(host: webserial, topic: str, request):
	response = [topic+"#dump", {"test": "123"}]
	host.send(json.dumps(response))


hal9000_commands = dict()
hal9000_commands["system/application"] = system_application
hal9000_commands["system/runtime"] = system_runtime

host = webserial(False, True)
host.connect()
host.status = "booting"
host.run(handler)

