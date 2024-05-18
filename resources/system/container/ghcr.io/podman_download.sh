#!/bin/bash

USER_UID=`/usr/bin/id -u`
USER_NAME=`/usr/bin/id -un`

TARGET_TAG=""
case $1 in
	development)
		TARGET_TAG="development"
		;;
	stable)
		TARGET_TAG="stable"
		;;
	*)
		echo "ERROR: please provide either 'development' or 'stable' as a parameter (used as the tag for pulling the images)"
		echo "       ./install.sh [development|stable]"
		exit 1
		;;
esac

if [ "x$USER_UID" == "x0" ]; then
	echo "ERROR: this script should NOT be run as root, use a non-privileged user (probably with dialout and audio as required group memberships, YMMV)"
	exit 1
fi

if [ "x$XDG_RUNTIME_DIR" == "x" ]; then
	echo "ERROR: for connecting with the user-instance of systemd, the environment variable XDG_RUNTIME_DIR must be set (export XDG_RUNTIME_DIR=/run/user/$USER_UID/)"
	exit 1
fi

podman pod exists hal9000
if [ x"$?" == "x0" ]; then
	echo "ERROR: pod 'hal9000' exists, aborting script (remove pod and start script again => podman pod rm hal9000)"
	exit 1 
fi

HAL9000_CONTAINERS=0
for NAME in mosquitto console frontend kalliope brain ; do
	podman container exists "hal9000-$NAME"
	if [ "x$?" == "x0" ]; then
		echo "ERROR: container 'hal9000-$NAME' exists, aborting script (remove container and start script again => podman container rm hal9000-$NAME)"
		HAL9000_CONTAINERS+=1
	fi
done
if [ "x$HAL9000_CONTAINERS" != "x0" ]; then
	exit 1
fi

for NAME in mosquitto console frontend kalliope brain ; do
	echo "Downloading image 'hal9000-$NAME:$TARGET_TAG'...."
	podman pull -q ghcr.io/juergenpabel/hal9000-$NAME:$TARGET_TAG
	if [ "x$?" != "x0" ]; then
		echo "ERROR:  download failed for 'ghcr.io/juergenpabel/hal9000-$NAME:$TARGET_TAG' - please investigate"
		exit 1
	fi
done

echo "INFO:   Downloading of images finished, next up: start containers"
echo "        ./podman_create.sh $TARGET_TAG # to create/configure containers"

