#!/usr/bin/python3

import os
import sys
import time
from threading import Thread
from configparser import ConfigParser

#from uwsgi import accepting
from hal9000.daemon.daemon import Daemon


config = ConfigParser(delimiters='=', converters={'list': lambda list: [item.strip() for item in list.split(',')]})
config.read(sys.argv[1])

peripherals = config.getlist('daemon', 'peripherals')
for peripheral in peripherals:
	daemon = Daemon(peripheral)
	daemon.load(sys.argv[1])
	Thread(target=daemon.loop).start()

#accepting()

while True:
	time.sleep(1)

