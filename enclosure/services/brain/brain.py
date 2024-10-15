#!/usr/bin/env python3

from sys import argv as sys_argv, \
                exit as sys_exit
from asyncio import run as asyncio_run
from logging import getLogger as logging_getLogger
from traceback import format_exception as traceback_format_exception

from hal9000.brain.daemon import Brain


if __name__ == '__main__':
	if len(sys_argv) != 2:
		logging_getLogger('brain').critical("usage: brain.py <CONFIG-FILE>")
		sys_exit(1)
	try:
		brain = Brain()
		brain.configure(sys_argv[1])
		results = asyncio_run(brain.loop())
		for name, result in results.items():
			if result is not None:
				logging_getLogger('brain').critical(f"[brain] asyncio_run(brain.loop()): '{name}' => {result}")
				if isinstance(result, Exception):
					logging_getLogger('brain').debug(traceback_format_exception(result))
			else:
				logging_getLogger('brain').debug(f"[brain] asyncio_run(brain.loop()): '{name}' => {result}")
	except Exception as e:
		logging_getLogger('brain').critical(f"[brain] {e}")
		raise e

