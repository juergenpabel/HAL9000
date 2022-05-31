#!/usr/bin/python3

import os
import sys
import time
from configparser import ConfigParser

from hal9000.daemon import DaemonLoader
#from uwsgi import accepting


Daemon = DaemonLoader(sys.argv[1]).import_daemon('hal9000.display')
daemon = Daemon()
daemon.load(sys.argv[1])
daemon.loop()

