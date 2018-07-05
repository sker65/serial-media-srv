# serial-media-srv
a media server that plays movies or images controlled by serial cmds.

This server could be used in various devices to playback movies or images based on the received serial commands.

# install on raspbian

apt-get update

apt-get install omxplayer

apt-get install fbset

apt-get install fbi

apt-get install fim

apt-get install python3-setuptools

apt-get install python3-dbus

apt-get install python3-pip

python3 -m pip install decorator

python3 -m pip install evento

python3 -m pip install pyserial

apt-get install git

git clone https://github.com/schlizbaeda/yamuplay.git

## in omxplayer directory
python3 setup.py install

usermod -a -G dialout,tty,video pi

chmod g+r /dev/ttyS0

in config.txt add 'enable_uart=1'

-> reboot

systemctl stop serial-getty@ttyS0

systemctl disable serial-getty@ttyS0

# start

python3 img-mov-srv.py [ basedir ]
