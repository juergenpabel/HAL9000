#!/usr/bin/python3

from webserial import webserial

hal9000 = webserial(True, True)
hal9000.connect()
hal9000.send('["device:microcontroller", {"reset": true}]')
hal9000.run()

