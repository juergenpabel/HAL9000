#!/usr/bin/python3
import sys

from kalliope import main as kalliope

sys.argv[0] = 'kalliope'
sys.argv.append('--debug')
sys.argv.append('start')
sys.exit(kalliope())

