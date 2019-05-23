#!/bin/bash

# usb stick support: detect if this path exists, if so use it as base path for update, soundset logging
BASEPATH=/boot
if [ -d /media/usb0/data ]; then
	BASEPATH=/media/usb0
fi
if [ -d /media/usb1/data ]; then
	BASEPATH=/media/usb1
fi
if [ -b /dev/sda ]; then
	BASEPATH=/media/usb
fi

# copy default jpg if missing
if [ ! -f $BASEPATH/data/default.jpg ]; then
    cp /boot/data/default.jpg $BASEPATH/data/
fi

# update handling
if [ -f $BASEPATH/update/update.zip ]; then
    mv $BASEPATH/update/update.zip $BASEPATH/update/update-done.zip
    unzip -o $BASEPATH/update/update-done.zip -d /home/pi/serial-media-srv
    sync
fi

# log rotate
mv $BASEPATH/data/serial1.log $BASEPATH/data/serial2.log
mv $BASEPATH/data/serial.log $BASEPATH/data/serial1.log

cd $BASEPATH/data
python3 /home/pi/serial-media-srv/img-mov-serial.py  >> $BASEPATH/data/serial.log 2>&1
