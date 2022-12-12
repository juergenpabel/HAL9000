#!/bin/bash

DEVICE="/dev/ttyHAL9000"
if [[ "x$1" != "x" ]]; then
	DEVICE="$1"
fi

echo "Creating (virtual) device sockets..."
if [[ -e "${DEVICE}" ||  -e "${DEVICE}.py" ]]; then
	echo "At least one of the devices ('${DEVICE}', '${DEVICE}.py') already exists, exiting."
	exit 0
fi
screen -dmS hal9000-socat socat -d -d pty,raw,echo=0,link="${DEVICE}" pty,raw,echo=0,link="${DEVICE}.py"
sleep 1
if [[ ! -L "${DEVICE}" ||  ! -L "${DEVICE}.py" ]]; then
	echo "At least one of the devices ('${DEVICE}', '${DEVICE}.py') could not be created (probably a /dev permissions issue, use /tmp/... instead), exiting."
	screen -q -XS hal9000-socat quit 2>&1 >/dev/null
	exit 0
fi


echo "Running virtual HAL9000, bound to '${DEVICE}.py' (use '${DEVICE}' as device)..."
./hal9000.py "${DEVICE}.py"

echo "Removing (virtual) device sockets..."
screen -q -XS hal9000-socat quit 2>&1 >/dev/null

echo "Done."

