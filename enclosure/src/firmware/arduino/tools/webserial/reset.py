#!/usr/bin/python3

from webserial import webserial

mcu = webserial(True, True)
mcu.connect()
mcu.send('["system/microcontroller", {"reset": "true"}]')
mcu.run()

