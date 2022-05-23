#!/usr/bin/python3

import sys
from uwsgi import accepting
from daemon import Daemon

filename = None
if len(sys.argv) > 1):
	filename = sys.argv[1]

daemon = Daemon()
daemon.configure(filename)

accepting()

daemon.loop()

