#!/bin/bash

case `/usr/bin/uname -o` in
	GNU/Linux)
		HOST_PLATFORM_OS="linux"
		;;
	*)
		echo "ERROR: unknown operating system, please add mapping to this script and run again (or specify via BUILD_PLATFORMS=...)"
		exit 1
		;;
esac
case `/usr/bin/uname -m` in
	aarch64)
		HOST_PLATFORM_HW="arm64"
		;;
	x86_64)
		HOST_PLATFORM_HW="amd64"
		;;
	*)
		echo "ERROR: unknown hardware platform, please add mapping to this script and run again (or specify via BUILD_PLATFORMS=...)"
		exit 1
		;;
esac
if [ "x$BUILD_PLATFORMS" == "x" ]; then
	BUILD_PLATFORMS="$HOST_PLATFORM_OS/$HOST_PLATFORM_HW"
fi
if [ "x$CONFIG_DIRECTORY" == "x" ]; then
	CONFIG_DIRECTORY="demo-en_US"
fi

echo "Building images for platforms '$BUILD_PLATFORMS' with language-related configurations from '$CONFIG_DIRECTORY'"
echo " "

SCRIPT_PATH=$(realpath "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
cd "$SCRIPT_DIR"
GIT_REPODIR=`git rev-parse --show-toplevel`
cd - >/dev/null
echo "Using '$GIT_REPODIR' as the repository base directory"
cd "$GIT_REPODIR"
git submodule init

echo "Building image 'hal9000-mosquitto'..."
podman manifest exists localhost/hal9000-mosquitto:latest >/dev/null
if [ "x$?" == "x0" ]; then
	podman manifest rm     localhost/hal9000-mosquitto:latest >/dev/null
fi
podman manifest create localhost/hal9000-mosquitto:latest > /dev/null
echo "$BUILD_PLATFORMS" | sed 's/,/\n/g' | while read BUILD_PLATFORM; do
	BUILD_PLATFORM_HW=`echo $BUILD_PLATFORM | sed 's#linux/##'`
	podman image rm docker.io/library/eclipse-mosquitto:latest 2>/dev/null
	podman pull --platform $BUILD_PLATFORM docker.io/library/eclipse-mosquitto:latest
	podman tag    docker.io/library/eclipse-mosquitto:latest localhost/hal9000-mosquitto:$BUILD_PLATFORM_HW
	podman image rm  docker.io/library/eclipse-mosquitto:latest 2>/dev/null
	podman manifest add localhost/hal9000-mosquitto:latest  containers-storage:localhost/hal9000-mosquitto:$BUILD_PLATFORM_HW
done

echo "Building image 'hal9000-kalliope'..."
cd "$GIT_REPODIR/kalliope"
git submodule update --recursive "$CONFIG_DIRECTORY"
podman manifest exists localhost/hal9000-kalliope:latest
if [ "x$?" == "x0" ]; then
	podman manifest rm localhost/hal9000-kalliope:latest
fi
podman build --platform "$BUILD_PLATFORMS" --build-arg KALLIOPE_CONFIG_DIRECTORY="$CONFIG_DIRECTORY" --manifest localhost/hal9000-kalliope:latest -f Containerfile .

echo "Building image 'hal9000-frontend'..."
cd "$GIT_REPODIR/enclosure/services/frontend/"
git submodule update --recursive "$CONFIG_DIRECTORY"
if [ ! -e "$CONFIG_DIRECTORY/assets" ]; then
	ln -s ../assets $CONFIG_DIRECTORY/assets
fi
podman manifest exists localhost/hal9000-frontend:latest
if [ "x$?" == "x0" ]; then
	podman manifest rm localhost/hal9000-frontend:latest
fi
podman build --platform "$BUILD_PLATFORMS" --build-arg FRONTEND_CONFIG_DIRECTORY="$CONFIG_DIRECTORY" --manifest localhost/hal9000-frontend:latest -f Containerfile .

echo "Building image 'hal9000-brain'..."
cd "$GIT_REPODIR/enclosure/services/brain/"
git submodule update --recursive "$CONFIG_DIRECTORY"
podman manifest exists localhost/hal9000-brain:latest
if [ "x$?" == "x0" ]; then
	podman manifest rm localhost/hal9000-brain:latest
fi
podman build --platform "$BUILD_PLATFORMS" --build-arg BRAIN_CONFIG_DIRECTORY="$CONFIG_DIRECTORY" --manifest localhost/hal9000-brain:latest -f Containerfile .

echo "Building image 'hal9000-console'..."
cd "$GIT_REPODIR/enclosure/services/console/"
git submodule update --recursive "$CONFIG_DIRECTORY"
if [ ! -e "$CONFIG_DIRECTORY/assets" ]; then
	ln -s ../assets $CONFIG_DIRECTORY/assets
fi
podman manifest exists localhost/hal9000-console:latest
if [ "x$?" == "x0" ]; then
	podman manifest rm localhost/hal9000-console:latest
fi
podman build --platform "$BUILD_PLATFORMS" --build-arg CONSOLE_CONFIG_DIRECTORY="$CONFIG_DIRECTORY" --manifest localhost/hal9000-console:latest -f Containerfile .

echo "NOTICE: images should be ready; next up: create pod/containers:"
echo "          ./podman_create.sh"

