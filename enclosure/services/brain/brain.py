#!/usr/bin/env python3

from sys import argv as sys_argv, \
                exit as sys_exit
from asyncio import run as asyncio_run
from logging import getLogger as logging_getLogger

from hal9000.brain.daemon import Daemon


if __name__ == '__main__':
	if len(sys_argv) != 2:
		logging_getLogger('brain').critical("usage: brain.py <CONFIG-FILE>")
		sys_exit(1)
	try:
		daemon = Daemon()
		daemon.configure(sys_argv[1])
		results = asyncio_run(daemon.loop())
		for name, result in results.items():
			if result is not None:
				logging_getLogger('brain').critical(f"asyncio_run(daemon.loop()): '{name}' => {result}")
			else:
				logging_getLogger('brain').debug(f"asyncio_run(daemon.loop()): '{name}' => {result}")
	except Exception as e:
		logging_getLogger('brain').critical(f"{e}")
		raise e

