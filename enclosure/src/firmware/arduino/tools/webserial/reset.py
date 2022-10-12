#!/usr/bin/python3

from webserial import webserial

mcu = webserial()
mcu.connect(False)
mcu.send('["system/mcu", {"reset": "true"}]')
mcu.run()

