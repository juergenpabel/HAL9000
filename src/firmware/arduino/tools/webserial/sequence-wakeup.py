#!/usr/bin/python3

import json
import time
from datetime import datetime, timezone
from webserial import webserial


hal9000 = webserial()
hal9000.connect()
hal9000.send('["gui:screen",  {"hal9000": {"queue": "replace", "sequence": [{"name": "wakeup", "timeout": 0}, {"name": "active", "timeout": 10}, {"name": "sleep", "timeout": 0}, {"name": "standby", "timeout": 0}]}}]')
hal9000.run()

