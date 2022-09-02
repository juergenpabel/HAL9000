#!/bin/bash

cd `dirname "${BASH_SOURCE[0]}"`

cp conf/modprobe.d/* /etc/modprobe.d/

apt update
apt upgrade -y
apt install -y python3 python3-pip mosquitto uwsgi uwsgi-plugin-python3 python3-uwsgidecorators python3-paho-mqtt python3-willow python3-numpy libportaudio2

systemctl stop uwsgi
systemctl enable uwsgi

groupadd --system --force hal9000
mkdir -p /opt/hal9000
chown root.hal9000 /opt/hal9000
chmod 750          /opt/hal9000

### enclosure ###
useradd --home-dir / -g hal9000 -G sudo,audio -M -N -r -s /bin/false hal9000
cp conf/mosquitto/conf.d/enclosure.conf /etc/mosquitto/conf.d/hal9000-enclosure.conf
systemctl restart mosquitto

pip3 install -r ../../../enclosure/src/requirements.txt
cp -r --dereference ../../../enclosure/src /opt/hal9000/enclosure
cat conf/uwsgi/enclosure.ini \
	| sed 's#/data/git/HAL9000-kalliope/enclosure/src#/opt/hal9000/enclosure#g' \
	| sed 's#/data/git/HAL9000-kalliope/resources/images#/opt/hal9000/enclosure/images#g' \
	| sed 's#app/enclosure/dummy#app/hal9000-enclosure/dummy#g' \
	> /etc/uwsgi/apps-enabled/hal9000-enclosure.ini


### kalliope ###
useradd --home-dir / -g kalliope -G audio,sudo -M -N -r -s /bin/false kalliope
cp conf/sudo/sudoers.d/100_kalliope /etc/sudoers.d/100_kalliope

pip3 install -r ../../../kalliope/src/requirements.txt
cp -r --dereference ../../../kalliope/src /opt/hal9000/kalliope
cp -r --dereference ../../../kalliope/brains /opt/hal9000/kalliope/
cp -r --dereference ../../../kalliope/scripts /opt/hal9000/kalliope/
chown -R root.kalliope /opt/hal9000/kalliope
chmod -R 770           /opt/hal9000/kalliope
cp conf/uwsgi/kalliope.ini /etc/uwsgi/apps-enabled/kalliope.ini

echo -n "List of preconfigured brain languages: "
( cd /opt/hal9000/kalliope/brains/ ; ls -d *-* )
read -p "Please enter language: " BRAIN
ln -s /opt/hal9000/kalliope/brains/"$BRAIN" /opt/hal9000/kalliope/brains/active

cd /opt/hal9000/kalliope/brains/active/
kalliope install --git-url https://github.com/kalliope-project/kalliope_trigger_precise.git
kalliope install --git-url https://github.com/juergenpabel/kalliope_stt_vosk.git
kalliope install --git-url https://github.com/juergenpabel/kalliope_neuron_sonos.git

rm -rf /tmp/kalliope

chown -R root.hal9000 /opt/hal9000
find /opt/hal9000 -type d              -exec chmod 750 {} \;
find /opt/hal9000 -type f              -exec chmod 640 {} \;
find /opt/hal9000 -type f -name "*.py" -exec chmod 750 {} \;
find /opt/hal9000 -type f -name "*.sh" -exec chmod 750 {} \;

echo "Please download a corresponding language model (small version) from https://alphacephei.com/vosk/models/ and extract it into /opt/hal9000/kalliope/brains/active/resources/data/vosk/"
echo "Please verify installed configuration and reboot"

