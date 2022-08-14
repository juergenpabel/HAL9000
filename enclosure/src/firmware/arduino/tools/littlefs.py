#!/usr/bin/python3

import os
import os.path
import sys
import glob
import subprocess

SRC_BASEDIR="./resources/images/frames"
DST_BASEDIR="./data/images/frames"
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
		PNG = "{}/{}".format(DST_BASEDIR, os.path.basename(BMP).replace(".bmp", ".png"))
		print(PNG)
		subprocess.run(["convert", BMP, "-resize", "240x240", PNG])


SRC_BASEDIR="./resources/images/overlay"
DST_BASEDIR="./data/images/overlay"
if os.path.exists("./data/images/overlay") is False:
	os.makedirs("./data/images/overlay")
	for DIR in ['volume']:
		if os.path.exists("{}/{}".format(DST_BASEDIR,DIR)) is False:
			os.makedirs("{}/{}".format(DST_BASEDIR,DIR))
		for PNG in glob.glob("{}/{}/*.png".format(SRC_BASEDIR,DIR)):
			subprocess.run(["convert", PNG, "-resize", "28x28", "{}/{}/{}".format(DST_BASEDIR,DIR,os.path.basename(PNG))])

if os.path.exists("./data/system") is False:
	os.makedirs("./data/system")

