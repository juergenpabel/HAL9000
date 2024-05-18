#!/bin/bash

USER_UID=`/usr/bin/id -u`
USER_NAME=`/usr/bin/id -un`

if [ "x$USER_UID" == "x0" ]; then
	echo "ERROR: this script should NOT be run as root, use a non-privileged user (probably with dialout and audio as required group memberships, YMMV)"
	exit 1
fi

if [ "x$XDG_RUNTIME_DIR" == "x" ]; then
	echo "ERROR: for connecting with the user-instance of systemd, the environment variable XDG_RUNTIME_DIR must be set => 'export XDG_RUNTIME_DIR=/run/user/$USER_UID/'"
	exit 1
fi

podman pod exists hal9000
if [ "x$?" != "x0" ]; then
	echo "ERROR: pod 'hal9000' does not exist, aborting script (create pod => './podman_create.sh' and than run this script again => './podman_deploy.sh')"
 
	exit 1 
fi

echo "Generating systemd files (in ~/.config/systemd/user)..."
mkdir -p ~/.config/systemd/user
cd ~/.config/systemd/user
podman generate systemd -n -f --start-timeout 5 --stop-timeout 5 hal9000
cd - >/dev/null

echo "Reloading systemd (user instance)..."
systemctl --user daemon-reload

echo "Enabling pod-hal9000.service in systemd (user instance)..."
systemctl --user enable pod-hal9000.service

echo "Starting pod 'hal9000'... (via 'systemd --user' with systemd lifecycle-management)"
systemctl --user start pod-hal9000.service

LINGER=`loginctl list-users | grep "^$USER_UID " | cut -d' ' -f 3`
if [ "x$LINGER" != "xyes" ]; then
	echo "NOTICE: sudo loginctl enable-linger $USER_NAME  # for automatic startup of a 'systemd --user' instance during system boot"
fi

if [ ! -e /dev/ttyHAL9000 ]; then
	echo "NOTICE: no mircocontroller (/dev/ttyHAL9000) detected, not mounting the device into the container 'hal9000-frontend'"
	echo "        use the web-frontend (http://127.0.0.1:9000) as the user-interface"
fi

