#!/usr/bin/python3

import os
import os.path
import sys
import glob
import subprocess

SRC_BASEDIR="../../../../resources/images/"
DST_BASEDIR="./images/"
for DIR in ['init','wakeup','active','wait','sleep','standby']:
	if os.path.exists("{}/{}".format(DST_BASEDIR,DIR)) is False:
		os.makedirs("{}/{}".format(DST_BASEDIR,DIR))
	for BMP in glob.glob("{}/{}/*.bmp".format(SRC_BASEDIR,DIR)):
		print(BMP)
		PNG = "{}/{}/{}".format(DST_BASEDIR, DIR, os.path.basename(BMP).replace(".bmp", ".png"))
		print(PNG)
		subprocess.run(["convert", BMP, "-quality", "75%", "-resize", "240x240", PNG])
		subprocess.run(["./tools/image_alpha.sh", PNG])

