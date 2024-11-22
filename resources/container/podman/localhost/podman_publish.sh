#!/bin/sh

CONTAINER_REGISTRY="${1:-unknown}"
CONTAINER_REPOSITORY="${2:-unknown}"
CONTAINER_TAG="${3:-unknown}"

if [ "${CONTAINER_REGISTRY}" = "unknown" ]; then
	echo "Usage: ./podman_publish.sh <container-registry-domain> <container-repository-path/user> <container-tag>"
	exit 1
fi
if [ "${CONTAINER_REPOSITORY}" = "unknown" ]; then
	echo "Usage: ./podman_publish.sh ${CONTAINER_REGISTRY} <container-repository-path/user> <container-tag>"
	exit 1
fi
if [ "${CONTAINER_TAG}" = "unknown" ]; then
	echo "Usage: ./podman_publish.sh ${CONTAINER_REGISTRY} ${CONTAINER_REPOSITORY} <container-tag>"
	exit 1
fi

echo "Logging in for '$CONTAINER_REGISTRY'..."
podman login "${CONTAINER_REGISTRY}"
if [ $? -ne 0 ]; then
	echo "ERROR: login failed for '${CONTAINER_REGISTRY}'"
	exit 1
fi
echo "INFO:  login successful"

echo "Publishing images to '${CONTAINER_REGISTRY}/${CONTAINER_REPOSITORY}/...' (with tag '${CONTAINER_TAG}')..."
UPLOAD_FAILED=""
for NAME in mosquitto kalliope frontend dashboard brain ; do
	echo "Publishing 'localhost/hal9000-${NAME}:latest' to '${CONTAINER_REGISTRY}/${CONTAINER_REPOSITORY}/hal9000-${NAME}:${CONTAINER_TAG}'..."
	podman manifest push "localhost/hal9000-${NAME}:latest" "${CONTAINER_REGISTRY}/${CONTAINER_REPOSITORY}/hal9000-${NAME}:${CONTAINER_TAG}"
	if [ $? -ne 0 ]; then
		UPLOAD_FAILED="${UPLOAD_FAILED}hal9000-${NAME} "
		echo "NOTICE: Upload failed for 'hal9000-${NAME}'"
	fi
done

if [ "x${UPLOAD_FAILED}" != "x" ]; then
	echo "ERROR: Upload failed for: ${UPLOAD_FAILED}"
	exit 1
fi

echo "INFO:   images should be uploaded now"

