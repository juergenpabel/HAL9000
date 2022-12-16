#!/usr/bin/python3

import os
import os.path
import sys
import glob
import shutil
import subprocess

SRC_BASEDIR="./resources/images/sequences"
DST_BASEDIR="./data/images/sequences"
if os.path.exists(DST_BASEDIR) is False:
	for DIR in ['init','wakeup','active','wait','sleep','standby']:
		if os.path.exists("{}/{}".format(DST_BASEDIR,DIR)) is False:
			os.makedirs("{}/{}".format(DST_BASEDIR,DIR))
		for BMP in glob.glob("{}/{}/*.bmp".format(SRC_BASEDIR,DIR)):
			print(BMP)
			JPG = "{}/{}/{}".format(DST_BASEDIR, DIR, os.path.basename(BMP).replace(".bmp", ".jpg"))
			print(JPG)
			subprocess.run(["convert", BMP, "-quality", "95%", "-resize", "120x120", "-scale", "240x240", JPG])
			subprocess.run(["mogrify", "-crop", "120x120+0+0", JPG])


SRC_BASEDIR="./resources/images/splash"
DST_BASEDIR="./data/images/splash"
if os.path.exists(DST_BASEDIR) is False:
	os.makedirs(DST_BASEDIR)
	for BMP in glob.glob("{}/*.bmp".format(SRC_BASEDIR)):
		print(BMP)
		JPG = "{}/{}".format(DST_BASEDIR, os.path.basename(BMP).replace(".bmp", ".jpg"))
		print(JPG)
		subprocess.run(["convert", BMP, "-quality", "95%", "-resize", "240x240", JPG])


SRC_BASEDIR="./resources/images/animations"
DST_BASEDIR="./data/images/animations"
if os.path.exists(DST_BASEDIR) is False:
	for DIR in ['startup','shutdown']:
		if os.path.exists("{}/{}".format(DST_BASEDIR,DIR)) is False:
			os.makedirs("{}/{}".format(DST_BASEDIR,DIR))
		shutil.copy("{}/{}.json".format(SRC_BASEDIR,DIR), DST_BASEDIR)
	for DIR in ['startup/boot','startup/countdown','shutdown']:
		if os.path.exists("{}/{}".format(DST_BASEDIR,DIR)) is False:
			os.makedirs("{}/{}".format(DST_BASEDIR,DIR))
		shutil.copy("{}/{}/animation.json".format(SRC_BASEDIR,DIR), "{}/{}".format(DST_BASEDIR,DIR))
		for SRC in glob.glob("{}/{}/*.jpg".format(SRC_BASEDIR,DIR)):
			print(SRC)
			DST = "{}/{}/{}".format(DST_BASEDIR, DIR, os.path.basename(SRC))
			print(DST)
			subprocess.run(["convert", SRC, "-resize", "240x240", "-background", "black", "-compose", "Copy", "-gravity", "center", "-extent", "240x240", DST])


SRC_BASEDIR="./resources/images/overlay"
DST_BASEDIR="./data/images/overlay"
if os.path.exists("./data/images/overlay") is False:
	os.makedirs("./data/images/overlay")
	for DIR in ['volume']:
		if os.path.exists("{}/{}".format(DST_BASEDIR,DIR)) is False:
			os.makedirs("{}/{}".format(DST_BASEDIR,DIR))
		for JPG in glob.glob("{}/{}/*.jpg".format(SRC_BASEDIR,DIR)):
			subprocess.run(["convert", JPG, "-quality", "95%", "-resize", "28x28", "{}/{}/{}".format(DST_BASEDIR,DIR,os.path.basename(JPG))])

if os.path.exists("./data/system") is False:
	os.makedirs("./data/system")
	with os.open("./data/system/settings.ini", os.O_CREAT):
		pass

