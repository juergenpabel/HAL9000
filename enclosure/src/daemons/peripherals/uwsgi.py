#!/usr/bin/python3

import os
import sys
import time
from threading import Thread
from configparser import ConfigParser

#from uwsgi import accepting


from hal9000.daemon import DaemonLoader

loader = DaemonLoader(sys.argv[1])
Daemon = loader.import_daemon('hal9000.peripherals.daemon')
for name in loader.get_daemon_threads():
	daemon = Daemon(name)
	daemon.load(sys.argv[1])
	Thread(target=daemon.loop).start()

#accepting()

while True:
	time.sleep(1)

