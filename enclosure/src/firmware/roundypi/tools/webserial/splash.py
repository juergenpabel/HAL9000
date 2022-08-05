#!/usr/bin/python3

import sys
from webserial import webserial

filename = "error.jpg"
if len(sys.argv) > 2:
	filename = sys.argv[2]

roundypi = webserial()
roundypi.connect()
roundypi.send('["screen:splash", {"filename": "%s"}]' % (filename))
roundypi.run()
