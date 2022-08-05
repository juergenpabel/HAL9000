#!/usr/bin/python3

import os
import os.path
import sys
import glob
import subprocess

SRC_BASEDIR="./resources/images"
DST_BASEDIR="./data/images/sequences"
if os.path.exists(DST_BASEDIR) is False:
	for DIR in ['init','wakeup','active','wait','sleep','standby']:
		if os.path.exists("{}/{}".format(DST_BASEDIR,DIR)) is False:
			os.makedirs("{}/{}".format(DST_BASEDIR,DIR))
		for BMP in glob.glob("{}/{}/*.bmp".format(SRC_BASEDIR,DIR)):
			print(BMP)
			PNG = "{}/{}/{}".format(DST_BASEDIR, DIR, os.path.basename(BMP).replace(".bmp", ".png"))
			print(PNG)
			subprocess.run(["convert", BMP, "-quality", "75%", "-resize", "120x120", "-scale", "240x240", PNG])
			subprocess.run(["mogrify", "-crop", "120x120+0+0", PNG])


SRC_BASEDIR="./resources/images/splash"
DST_BASEDIR="./data/images/splash"
if os.path.exists(DST_BASEDIR) is False:
	os.makedirs(DST_BASEDIR)
	for BMP in glob.glob("{}/*.bmp".format(SRC_BASEDIR)):
		print(BMP)
		JPG = "{}/{}".format(DST_BASEDIR, os.path.basename(BMP).replace(".bmp", ".jpg"))
		print(JPG)
		subprocess.run(["convert", BMP, "-resize", "240x240", JPG])

