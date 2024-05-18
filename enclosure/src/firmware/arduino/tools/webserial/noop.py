#!/usr/bin/python3

from webserial import webserial

hal9000 = webserial(True, True)
hal9000.connect()
hal9000.run()

