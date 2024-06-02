#!/bin/bash

USER_UID=`/usr/bin/id -u`
USER_NAME=`/usr/bin/id -un`
TARGET_TAG="$1"

if [ "x$USER_UID" == "x0" ]; then
	echo "ERROR: this script should NOT be run as root, use a non-privileged user (probably with dialout and audio as required group memberships, YMMV)"
	exit 1
fi

if [ "x$XDG_RUNTIME_DIR" == "x" ]; then
	echo "ERROR: for connecting with the user-instance of systemd, the environment variable XDG_RUNTIME_DIR must be set (export XDG_RUNTIME_DIR=/run/user/$USER_UID/)"
	exit 1
fi

if [ "x$TARGET_TAG" == "x" ]; then
	echo "ERROR: no target tag (most likely 'development' or 'stable') provided as a command parameter)"
	exit 1
fi

podman pod exists hal9000
if [ "x$?" == "x0" ]; then
	echo "ERROR: pod 'hal9000' exists, aborting script (remove pod and start script again => podman pod rm hal9000)"
	exit 1 
fi


MISSING_IMAGES=0
for NAME in mosquitto console frontend kalliope brain ; do
	podman image exists "ghcr.io/juergenpabel/hal9000-$NAME:$TARGET_TAG"
	if [ "x$?" != "x0" ]; then
		echo "ERROR:  image 'ghcr.io/juergenpabel/hal9000-$NAME:$TARGET_TAG' not found"
		MISSING_IMAGES+=1
	fi
done
if [ "x$MISSING_IMAGES" != "x0" ]; then
	echo "        Aborting script (download images first => ./podman_download.sh $TARGET_TAG)"
	exit 1
fi


DEVICE_TTYHAL9000_ARGS="--device /dev/ttyHAL9000:/dev/ttyHAL9000"
if [ ! -e /dev/ttyHAL9000 ]; then
	DEVICE_TTYHAL9000_ARGS=""
fi
SYSTEMD_TIMESYNC_ARGS="-v /run/systemd/timesync:/run/systemd/timesync:ro"
if [ ! -e /run/systemd/timesync ]; then
	SYSTEMD_TIMESYNC_ARGS=""
fi

echo -n "Creating pod 'hal9000': "
podman pod create --name hal9000 \
                  -p 127.0.0.1:8080:8080 \
                  -p 127.0.0.1:9000:9000 \
                  --network hal9000 \
                  --infra-name hal9000-infra \
                  --hostname hal9000

echo -n "Creating container 'hal9000-mosquitto': "
podman create --pod=hal9000 --name=hal9000-mosquitto \
              --group-add=keep-groups \
              --tz=local \
              --pull=never \
              ghcr.io/juergenpabel/hal9000-mosquitto:$TARGET_TAG

echo -n "Creating container 'hal9000-kalliope':  "
podman create --pod=hal9000 --name=hal9000-kalliope \
              --requires hal9000-mosquitto \
              --group-add=keep-groups \
              --device /dev/snd:/dev/snd \
              -v /etc/asound.conf:/etc/asound.conf:ro \
              --tz=local \
              --pull=never \
              ghcr.io/juergenpabel/hal9000-kalliope:$TARGET_TAG

echo -n "Creating container 'hal9000-frontend':  "
podman create --pod=hal9000 --name=hal9000-frontend \
              --requires hal9000-mosquitto \
              --group-add=keep-groups \
              $DEVICE_TTYHAL9000_ARGS \
              --tz=local \
              --pull=never \
              ghcr.io/juergenpabel/hal9000-frontend:$TARGET_TAG

echo -n "Creating container 'hal9000-brain':     "
podman create --pod=hal9000 --name=hal9000-brain \
              --requires hal9000-kalliope,hal9000-frontend \
              --group-add=keep-groups \
              --tz=local \
              -v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket:rw \
              $SYSTEMD_TIMESYNC_ARGS \
              --pull=never \
              ghcr.io/juergenpabel/hal9000-brain:$TARGET_TAG

echo -n "Creating container 'hal9000-console':   "
podman create --pod=hal9000 --name=hal9000-console \
              --requires hal9000-mosquitto \
              --group-add=keep-groups \
              --tz=local \
              --pull=never \
              ghcr.io/juergenpabel/hal9000-console:$TARGET_TAG

if [ "x$DEVICE_TTYHAL9000_ARGS" == "x" ]; then
	echo "NOTICE: no mircocontroller (/dev/ttyHAL9000) detected, not mounting the device into container 'hal9000-frontend'"
	echo "        use the web-frontend (http://127.0.0.1:9000) as the user-interface (an open session is required for HAL9000 startup completion)"
fi

echo "NOTICE: pod 'hal9000' created; next up: start pod/containers"
echo "        If you would like to start the hal9000 containers NOW, either:"
echo "          podman pod start hal9000  # for one-shot pod execution (and manual lifecycle handling)"
echo "        or"
echo "          ./run_systemd.sh          # for systemd-managed lifecycle execution (even after reboots)"

