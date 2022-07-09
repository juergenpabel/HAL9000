#!/bin/sh

DEVICE="/dev/ttyRP2040"
if [ "x$1" != "x" ]; then
	DEVICE="$1"
fi
echo "Rebooting $DEVICE to UF2..."
stty -F "$DEVICE" 1200

