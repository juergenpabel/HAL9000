#!/bin/sh

apt update
apt upgrade -y
apt install -y python3 python3-pip mosquitto uwsgi uwsgi-plugin-python3 python3-uwsgidecorators python3-paho-mqtt

groupadd --system --force hal9000
useradd --home-dir / -g hal9000 -G i2c,spi,gpio -M -N -r -s /bin/false hal9000-enclosure
useradd --home-dir / -g hal9000 -G sudo         -M -N -r -s /bin/false hal9000-kalliope

cat ../../../conf/sudo/sudoers.d/100_kalliope | sed 's#kalliope#hal9000-kalliope#g' > /etc/sudoers.d/100_hal9000-kalliope

cp ../../../conf/mosquitto/conf.d/enclosure.conf /etc/mosquitto/conf.d/hal9000-enclosure.conf
systemctl restart mosquitto


mkdir /opt/hal9000
chown root.hal9000 /opt/hal9000
chmod 750          /opt/hal9000

mkdir /opt/hal9000/enclosure
chown root.hal9000 /opt/hal9000/enclosure
chmod 750          /opt/hal9000/enclosure
cp -r ../../../src/enclosure /opt/hal9000/enclosure
cat ../../../conf/uwsgi/enclosure.ini | sed 's#/data/git/HAL9000-kalliope/#/opt/hal9000/#g' > /etc/uwsgi/apps-enabled/hal9000-enclosure.ini
systemctl restart uwsgi

mkdir /opt/hal9000/kalliope
chown root.hal9000 /opt/hal9000/kalliope
chmod 750          /opt/hal9000/kalliope

