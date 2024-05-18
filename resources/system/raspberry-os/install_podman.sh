#!/bin/bash

## This script is intented to run on a Raspberry Zero 2W with RaspbianOS 12 (bookworm).
## The script does the following:
## - update system packages
## - install git (for respeaker drivers) and podman (for downloading + running of containers with HAL9000 components)
## - install respeaker driver (the "original" system uses a respeaker 2-mic); 
##   - a custom git branch is maintained for the driver, based on the current kernel version a switch to that branch is made
##   - the number of parallel compile jobs is set to 1 (due to stability issues with 4 being the  default on a RPI Zero 2W)
## - install driver blacklists
## - install udev handlers for creating a symlink named /dev/ttyHAL9000
## - create a (non-privileged) user 'hal9000' and activates an on-boot started systemd user-instance
## - downloads the HAL9000 container images from ghcr.io (the HAL9000 software runs in those containers)
## - prompts the user to restart the system for... some HAL9000 fun (it should just work*TM*)


echo "HAL9000: Installation script (for podman+systemd based setups) starts in 3 secs..."
echo "         (CTRL-C right now, if unsure)"
sleep 3

cd ~

SYSTEM_MODEL=`cat /proc/cpuinfo | grep Model | cut -d' ' -f2-`
if [ "$SYSTEM_MODEL" == *"Raspberry Pi Zero 2 W"* ]; then
	echo "HAL9000: Disabling CPUs #2 and #3 to prevent hangups..."
	grep -q 'maxcpus=' /boot/firmware/cmdline.txt > /dev/null
	if [ "$?" != "0" ]; then
		sudo sed -i 's/$/ maxcpus=2/' /boot/firmware/cmdline.txt
	fi
	echo "HAL9000: Adding modprobe blacklist for 'ftdi' and 'vc4'..."
	sleep 1
	if [ ! -f /etc/modprobe.d/hal9000_blacklist-ftdi.conf ]; then
		sudo sh -c 'echo "blacklist ftdi_sio" > /etc/modprobe.d/hal9000_blacklist-ftdi.conf'
	fi
	if [ ! -f /etc/modprobe.d/hal9000_blacklist-vc4.conf ]; then
		sudo sh -c 'echo "blacklist vc4"      > /etc/modprobe.d/hal9000_blacklist-vc4.conf'
	fi
fi

echo "HAL9000: Updating and installing additional software packages..."
sleep 1
sudo apt update
sudo apt upgrade -y
sudo apt install -y git podman


echo "HAL9000: Downloading, building and installing soundcard driver (seeed-voicecard)..."
sleep 1
if [ ! -d seeed-voicecard ]; then
	git clone https://github.com/HinTak/seeed-voicecard
fi
cd seeed-voicecard
git checkout v`uname -r | cut -d. -f1-2`
sed -i 's/dkms build -k/dkms build -j 1 -k/g' install.sh
sudo ./install.sh 
cd ..


echo "HAL9000: Configuring udev for /dev/ttyHAL9000..."
sleep 1
if [ ! -f /etc/udev/rules.d/99-hal9000-tty.rules ]; then
	sudo sh -c 'echo "SUBSYSTEM!=\"tty\", GOTO=\"hal9000_tty_end\""                                   >>  /etc/udev/rules.d/99-hal9000-tty.rules'
	sudo sh -c 'echo "ACTION!=\"add\", GOTO=\"hal9000_tty_end\""                                      >>  /etc/udev/rules.d/99-hal9000-tty.rules'
	sudo sh -c 'echo "ATTRS{idVendor}==\"2e8a\", ATTRS{idProduct}==\"000a\", SYMLINK+=\"ttyHAL9000\"" >>  /etc/udev/rules.d/99-hal9000-tty.rules'
	sudo sh -c 'echo "ATTRS{idVendor}==\"1a86\", ATTRS{idProduct}==\"55d4\", SYMLINK+=\"ttyHAL9000\"" >>  /etc/udev/rules.d/99-hal9000-tty.rules'
	sudo sh -c 'echo "LABEL=\"hal9000_tty_end\""                                                      >>  /etc/udev/rules.d/99-hal9000-tty.rules'
	sudo udevadm control --reload-rules
	sudo udevadm trigger
fi

echo "HAL9000: Configuring udev for ALSA:HAL9000..."
sleep 1
if [ ! -f /etc/udev/rules.d/99-hal9000-alsa.rules ]; then
	sudo sh -c 'echo "SUBSYSTEM!=\"sound\", GOTO=\"hal9000_alsa_end\""                                              >> /etc/udev/rules.d/99-hal9000-alsa.rules'
	sudo sh -c 'echo "ACTION!=\"add\", GOTO=\"hal9000_alsa_end\""                                                   >> /etc/udev/rules.d/99-hal9000-alsa.rules'
	sudo sh -c 'echo "DEVPATH==\"/devices/platform/soc/soc:sound/sound/card?\", ATTR{id}=\"HAL9000\""               >> /etc/udev/rules.d/99-hal9000-alsa.rules'
	sudo sh -c 'echo "DEVPATH==\"/devices/pci0000:00/0000:00:08.1/0000:c1:00.6/sound/card?\", ATTR{id}=\"HAL9000\"" >> /etc/udev/rules.d/99-hal9000-alsa.rules'
	sudo sh -c 'echo "LABEL=\"hal9000_alsa_end\""                                                                   >> /etc/udev/rules.d/99-hal9000-alsa.rules'
	sudo udevadm control --reload-rules
	sudo udevadm trigger
fi


echo "HAL9000: Creating (non-privileged) user 'hal9000'..."
sleep 1
id hal9000 >/dev/null 2>/dev/null
if [ "$?" != "0" ]; then
	sudo groupadd -g 9000 hal9000 > /dev/null
	sudo useradd -g hal9000 -G audio,dialout -m  -s /bin/bash -u 9000 hal9000  > /dev/null
	sudo loginctl enable-linger hal9000  > /dev/null
	sudo -u hal9000 -i sh -c 'echo "export XDG_RUNTIME_DIR=/run/user/9000" >> ~/.profile'
fi


echo "HAL9000: Downloading container images..."
sleep 1
for NAME in mosquitto kalliope frontend console brain ; do
	echo "         - hal9000-$NAME"
	sudo -u hal9000 -i podman pull ghcr.io/juergenpabel/hal9000-$NAME:development
done


echo "HAL9000: ****************************************************************"
echo "HAL9000: *                   HAL9000 install finished                   *"
echo "HAL9000: ****************************************************************"
echo "HAL9000: Assuming this script ran on a 'freshly' installed RaspbianOS"
echo "HAL9000: system, it is recommended to execute the following commands to"
echo "HAL9000: further optimize security and to improve HAL9000 runtime"
echo "HAL9000: performance (copy+paste as you deem relevant):"
echo "HAL9000: sudo systemctl disable avahi-daemon.service"
echo "HAL9000: sudo systemctl disable avahi-daemon.socket"
echo "HAL9000: sudo systemctl disable bluetooth.service"
echo "HAL9000: sudo systemctl disable ModemManager.service"
echo "HAL9000: sudo sh -c 'echo \"gpu_mem=16\" >> /boot/firmware/config.txt'"

SYSTEM_RAM=`cat /proc/meminfo | grep MemTotal | grep -o '[[:digit:]]*'`
SYSTEM_SWAP=`cat /proc/meminfo | grep SwapTotal | grep -o '[[:digit:]]*'`
if [ $((SYSTEM_RAM + SYSTEM_SWAP)) -lt "1048572" ]; then
	echo "HAL9000: # IMPORTANT: if you want to BUILD container images, about 1GB  #"
	echo "         #            of memory (RAM+SWAP) must be available, or it     #"
	echo "         #            will not work (OOM). Since not enough memory is   #"
	echo "         #            detected, it is suggest to set the swap file size #"
	echo "         #            to 1GB, like so:                                  #"
	echo "         sudo sed -i 's/^CONF_SWAPSIZE=.*$/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile"
	echo "         sudo systemctl restart dphys-swapfile.service"
fi
if [ $((SYSTEM_SWAP)) -gt "0" ]; then
	echo "HAL9000: # IMPORTANT: if you only want to RUN container images, 512MB   #"
	echo "         #            of memory (RAM) are sufficient. The swap file can #"
	echo "         #            be disabled, like so (totally optional):          #"
	echo "         sudo systemctl disable dphys-swapfile.service"
fi
echo "HAL9000: ****************************************************************"
echo "HAL9000: *         In any case: restart your system and enjoy!          *"
echo "HAL9000: ****************************************************************"

