#!/usr/bin/python3

import sys

from hal9000.daemon.kalliope.agent.daemon import Daemon

daemon = Daemon()
daemon.load(sys.argv[1])
daemon.loop()

