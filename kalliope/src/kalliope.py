#!/usr/bin/python3
import sys

from uwsgi import accepting
from kalliope import main as kalliope

accepting()
sys.argv[0] = 'kalliope'
sys.argv.append('--debug')
sys.argv.append('start')
sys.exit(kalliope())

