#!/usr/bin/python3

import sys
from webserial import webserial

filename = "error.jpg"
if len(sys.argv) > 2:
	filename = sys.argv[2]

hal9000 = webserial(True, True)
hal9000.connect()
hal9000.send('["gui:screen", {"splash": {"filename": "%s"}}]' % (filename))
hal9000.run()
