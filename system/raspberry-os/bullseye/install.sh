#!/bin/bash

cd `dirname "${BASH_SOURCE[0]}"`

apt update
apt upgrade -y
apt install -y python3 python3-pip mosquitto uwsgi uwsgi-plugin-python3 python3-uwsgidecorators python3-paho-mqtt python3-willow python3-numpy

systemctl stop uwsgi
systemctl enable uwsgi

groupadd --system --force hal9000
mkdir -p /opt/hal9000
chown root.hal9000 /opt/hal9000
chmod 750          /opt/hal9000

### enclosure ###
useradd --home-dir / -g hal9000 -G plugdev,i2c,spi,gpio -M -N -r -s /bin/false hal9000-enclosure
cp conf/mosquitto/conf.d/enclosure.conf /etc/mosquitto/conf.d/hal9000-enclosure.conf
systemctl restart mosquitto

pip3 install -r ../../../enclosure/src/requirements.txt
cp -r --dereference ../../../enclosure/src /opt/hal9000/enclosure
chown -R root.hal9000 /opt/hal9000/enclosure
chmod -R 750          /opt/hal9000/enclosure
cat conf/uwsgi/enclosure.ini \
	| sed 's#/data/git/HAL9000-kalliope/enclosure/src#/opt/hal9000/enclosure#g' \
	| sed 's#/data/git/HAL9000-kalliope/resources/images#/opt/hal9000/enclosure/images#g' \
	| sed 's#app/enclosure/dummy#app/hal9000-enclosure/dummy#g' \
	> /etc/uwsgi/apps-enabled/hal9000-enclosure.ini


### kalliope ###
useradd --home-dir / -g hal9000 -G sudo                 -M -N -r -s /bin/false hal9000-kalliope
cat conf/sudo/sudoers.d/100_kalliope | sed 's#kalliope#hal9000-kalliope#g' > /etc/sudoers.d/100_hal9000-kalliope

pip3 install -r ../../../kalliope/src/requirements.txt
cp -r --dereference ../../../kalliope/src /opt/hal9000/kalliope
chown -R root.hal9000 /opt/hal9000/kalliope
chmod -R 750          /opt/hal9000/kalliope
cat conf/uwsgi/kalliope.ini \
	| sed 's#/data/git/HAL9000-kalliope/kalliope/src#/opt/hal9000/kalliope#g' \
	| sed 's#app/kalliope/dummy#app/hal9000-kalliope/dummy#g' \
	> /etc/uwsgi/apps-enabled/hal9000-kalliope.ini

systemctl start uwsgi

