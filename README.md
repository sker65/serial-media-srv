# serial-media-srv
a media server that plays movies or images controlled by serial cmds.

This server could be used in various devices to playback movies or images based on the received serial commands.

# running

There's a start script provided start.sh and a service definition for systemd as well (serial-media.service).
To install the service copy serial-media.service to /etc/systemd/system adjust installation path and start/enable the service by systemctl start/enable serial-media

# config

The service recognizes movies (mp4, 3gp, mov or avi) or images (jpg or png) in its working directory and will show / play it when it receives a two byte serial
command. The command is simply translated into a number which should match the file name. So if you send 02 03 over serial line it will play 2*256 + 3 = 515.avi

Besides the "numbered" media files it recognizes default images or movies by filenames starting with "default". If there is more than one it will be randomly picked
and played, if there is nothing else to play / show (also on startup).

# playback

if a numbered movie is still playing, while the same number is received again, it will be ignored. After movie finished the default images will be shown / default
movie will be played.

so far there is no slideshow or looping implemented.

# install on raspbian

Base image is raspian lite stretch. Then run / install the following commands ...

```
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
```

## in omxplayer directory

```
python3 setup.py install
usermod -a -G dialout,tty,video pi
chmod g+r /dev/ttyS0

in config.txt add 'enable_uart=1'

-> reboot

systemctl stop serial-getty@ttyS0
systemctl disable serial-getty@ttyS0
```

# start

python3 img-mov-srv.py [ basedir ] [ device ]
