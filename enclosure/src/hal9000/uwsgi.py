#!/usr/bin/python3


from uwsgi import accepting
from daemon import Daemon


daemon = Daemon()
daemon.configure()

accepting()

daemon.loop()

