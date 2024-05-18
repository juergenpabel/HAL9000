#!/bin/bash

CONTAINER_REGISTRY="$1"
CONTAINER_REPOSITORY="$2"
CONTAINER_TAG="$3"

if [ "x$1" == "x" ]; then
	echo "Usage: ./podman_publish.sh <container-registry-domain> <container-repository-path/user> <container-tag>"
	exit 1
fi
if [ "x$2" == "x" ]; then
	echo "Usage: ./podman_publish.sh $1 <container-repository-path/user> <container-tag>"
	exit 1
fi
if [ "x$3" == "x" ]; then
	echo "Usage: ./podman_publish.sh $1 $2 <container-tag>"
	exit 1
fi

echo "Logging in for '$CONTAINER_REGISTRY'..."
podman login $CONTAINER_REGISTRY
if [ "x$?" != "x0" ]; then
	echo "ERROR: login failed for '$CONTAINER_REGISTRY'"
	exit 1
fi
echo "INFO:  login successful"

echo "Publishing images to '$CONTAINER_REGISTRY/$CONTAINER_REPOSITORY/...' (with tag '$CONTAINER_TAG')..."
UPLOAD_FAILED=""
for CONTAINER_NAME in hal9000-mosquitto hal9000-kalliope hal9000-frontend hal9000-brain hal9000-console ; do
	echo "Publishing 'localhost/$CONTAINER_NAME:latest' to '$CONTAINER_REGISTRY/$CONTAINER_REPOSITORY/$CONTAINER_NAME:$CONTAINER_TAG'..."
	podman manifest push -q localhost/$CONTAINER_NAME:latest $CONTAINER_REGISTRY/$CONTAINER_REPOSITORY/$CONTAINER_NAME:$CONTAINER_TAG
	if [ "x$?" != "x0" ]; then
		UPLOAD_FAILED="$UPLOAD_FAILED$CONTAINER_NAME "
		echo "NOTICE: Upload failed for $CONTAINER_NAME"
	fi
done

if [ "x$UPLOAD_FAILED" != "x" ]; then
		echo "ERROR: Upload failed for: $UPLOAD_FAILED"
		exit 1
fi

echo "INFO:   images should be uploaded now"

