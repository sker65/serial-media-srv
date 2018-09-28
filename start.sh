#!/bin/bash
# update handling
if [ -f /boot/update/update.zip ]; then
    mv /boot/update/update.zip /boot/update/update-done.zip
    unzip -o /boot/update/update-done.zip -d /home/pi/serial-media-srv
    sync
fi

# log rotate
mv /boot/data/serial.log.1 /boot/data/serial.log.2
mv /boot/data/serial.log /boot/data/serial.log.1

cd /boot/data
python3 /home/pi/serial-media-srv/img-mov-serial.py  >> /boot/data/serial.log 2>&1
