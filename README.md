# serial-media-srv
a media server that plays movies or images controlled by serial cmds.

This server could be used in various devices to playback movies or images based on the received serial commands.

# running

There's a start script provided start.sh and a service definition for systemd as well (serial-media.service).
To install the service copy serial-media.service to /etc/systemd/system adjust installation path and start/enable the service by systemctl start/enable serial-media

# config

The service reads a config file (ini file) from the current directory by default (serial-media-srv.ini). It consists of sections see example. There a builtin defaults for showing images and also for playing movies that rely on omxplayer / fim.

# commands

Ther service reads commands from the serial port (or other input) just as one line. Commands are always uppercase and can have arguments.

## play command

```PLAY <media>``` 

plays / shows a media file (image / movie)

## stop command

```STOP```

stop any running media, go back to a default (if defined)

## playoneof command

```PLAYONEOF <media1> <media2> <media3> ```

plays one of the media files, chooses randomly

# movie playback
if a movie is playing the server remembers its name, so if the same movie is requested twice, the movie just plays on (no rewind or interruption)

# install on raspbian

Base image is raspian lite stretch or dietpi. Then run / install the following commands ...

```
Beginning with version 1.0.4 the serial media server is no longer using yamuplay or omxplayer python extension (didn't work).
There is also an image available to make the setup even easier, see here https://go-dmd.de/produkt/serial-media-server-image/

apt-get update
apt-get install omxplayer
apt-get install fbset
apt-get install fbi
apt-get install fim
apt-get install python3-setuptools
// apt-get install python3-dbus
apt-get install python3-pip

// python3 -m pip install decorator
// python3 -m pip install evento
python3 -m pip install pyserial

// apt-get install git
// git clone https://github.com/schlizbaeda/yamuplay.git
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

# image

There is also an image available based on raspbian stretch lite the could be written on a 16GB sd card using some imager tool
like Win32 Disk Imager or etcher. The image is even more customized as all startup messages on the screen are removed and a nice
start animation is shown instead. You can get the image here: https://go-dmd.de/produkt/serial-media-server-image/

# start

python3 img-mov-srv.py [ basedir ] [ device ]
