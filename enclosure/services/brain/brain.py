#!/usr/bin/env python3

import sys
from hal9000.brain.daemon import Daemon

daemon = Daemon()
daemon.configure(sys.argv[1])
daemon.loop()

