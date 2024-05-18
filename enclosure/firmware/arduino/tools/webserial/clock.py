#!/usr/bin/env python3

from webserial import webserial
import sys
import time
import select
import json
from datetime import datetime, timezone


hal9000 = webserial(True, True)
hal9000.connect()
hal9000.send('["application/runtime",  {"time": {"epoch": %d}}]' % (int(datetime.now().timestamp() + datetime.now().astimezone().tzinfo.utcoffset(None).seconds)))
hal9000.send('["gui/screen", {"idle": {}}]')
hal9000.run()

