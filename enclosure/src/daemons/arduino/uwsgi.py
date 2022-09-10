#!/usr/bin/python3

import sys
import time

from hal9000.arduino.daemon import Daemon

daemon = Daemon()
daemon.load(sys.argv[1])
daemon.loop()
daemon.drivers["rotary:volume"].send('["gui/screen", {"shutdown": {}}]')
time.sleep(0.1)

