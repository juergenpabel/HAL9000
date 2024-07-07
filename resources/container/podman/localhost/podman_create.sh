#!/bin/sh

podman pod exists hal9000
if [ $? -eq 0 ]; then
	echo "ERROR: pod 'hal9000' exists, aborting script (remove pod and start script again => podman pod rm hal9000)"
	exit 1 
fi

HAL9000_CONTAINERS=0
for NAME in mosquitto kalliope frontend console brain ; do
	podman container exists "hal9000-${NAME}"
	if [ $? -eq 0 ]; then
		echo "ERROR: container 'hal9000-${NAME}' exists, aborting script (remove container and start script again:"
		echo "       podman container rm 'hal9000-${NAME}')"
		HAL9000_CONTAINERS+=1
	fi
done
if [ ${HAL9000_CONTAINERS} -ne 0 ]; then
	exit 1
fi

SCRIPT_PATH=$(realpath "$0")
SCRIPT_DIR=$(dirname "${SCRIPT_PATH}")
cd "${SCRIPT_DIR}"
GIT_REPODIR=`git rev-parse --show-toplevel`
cd - >/dev/null
echo "Using '${GIT_REPODIR}' as the repository base directory (for volume mounts in containers)"

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
                  --network=host \
                  --infra-name hal9000-infra \
                  --hostname hal9000

echo -n "Creating container 'hal9000-mosquitto': "
podman create --pod=hal9000 --name=hal9000-mosquitto \
              --group-add=keep-groups \
              --tz=local \
              --pull=never \
              localhost/hal9000-mosquitto:latest

echo -n "Creating container 'hal9000-kalliope':  "
podman create --pod=hal9000 --name=hal9000-kalliope \
              --requires hal9000-mosquitto \
              --group-add=keep-groups \
              -v "${GIT_REPODIR}"/kalliope/:/kalliope/:ro \
              -v /etc/asound.conf:/etc/asound.conf:ro \
              --device /dev/snd:/dev/snd \
              --tz=local \
              --pull=never \
              localhost/hal9000-kalliope:latest

echo -n "Creating container 'hal9000-frontend':  "
podman create --pod=hal9000 --name=hal9000-frontend \
              --requires hal9000-mosquitto \
              --group-add=keep-groups \
              -v "${GIT_REPODIR}"/enclosure/services/frontend/:/frontend/:ro \
              ${DEVICE_TTYHAL9000_ARGS} \
              --tz=local \
              --pull=never \
              localhost/hal9000-frontend:latest

echo -n "Creating container 'hal9000-console':   "
podman create --pod=hal9000 --name=hal9000-console \
              --requires hal9000-mosquitto \
              --group-add=keep-groups \
              -v "${GIT_REPODIR}"/enclosure/services/console/:/console/:ro \
              --tz=local \
              --pull=never \
              localhost/hal9000-console:latest

echo -n "Creating container 'hal9000-brain':     "
podman create --pod=hal9000 --name=hal9000-brain \
              --requires hal9000-kalliope,hal9000-frontend \
              --group-add=keep-groups \
              -v "${GIT_REPODIR}"/enclosure/services/brain/:/brain/:ro \
              -v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket:rw \
              ${SYSTEMD_TIMESYNC_ARGS} \
              --tz=local \
              --pull=never \
              localhost/hal9000-brain:latest

if [ "x${DEVICE_TTYHAL9000_ARGS}" = "x" ]; then
	echo "NOTICE: no mircocontroller (/dev/ttyHAL9000) detected, not mounting the device into container 'hal9000-frontend'"
	echo "        use the web-frontend (http://127.0.0.1:9000) as the user-interface (an open session is required for HAL9000 startup completion)"
fi
echo "NOTICE: pod 'hal9000' created; next up: start pod/containers"
echo "        If you would like to start the hal9000 containers NOW, either:"
echo "          podman pod start hal9000  # for one-shot pod execution (and manual lifecycle handling)"
echo "        or"
echo "          ./podman_deploy.sh        # for systemd-managed lifecycle execution (even after reboots)"

