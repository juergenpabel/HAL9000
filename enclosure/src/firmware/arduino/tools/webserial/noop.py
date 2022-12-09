#!/usr/bin/python3

from webserial import webserial

mcu = webserial(True, True)
mcu.connect()
mcu.run()

