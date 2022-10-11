#!/usr/bin/python3

from webserial import webserial

mcu = webserial()
mcu.connect()
mcu.run()

