'''
    img-mov-serial.py

    Created on: 05.07.2018
      Author: Stefan Rinke
    https://github.com/sker65/serial-media-srv

    (C) 2017-2018 by Stefan Rinke / Rinke Solutions
    This work is licensed under a Creative
	Commons Attribution-NonCommercial-
	ShareAlike 4.0 International License.

	http://creativecommons.org/licenses/by-nc-sa/4.0/
'''
import os
import re
import serial
import subprocess
import sys
import random
import signal
import datetime
from shutil import copyfile

from pathlib import Path
from omxplayer.player import OMXPlayer

# refresh start.sh itself if necessary
newStart = Path("./new-start.sh")
if newStart.is_file():
    copyfile("./new-start.sh", "./start.sh")
    newStart.unlink()

version = '1.0.2'

basedir = '.'
if len(sys.argv) > 1:
    basedir = sys.argv[1]

serial_device = '/dev/ttyS0'
if len(sys.argv) > 2:
    serial_device = sys.argv[2]

def signal_handler(sig, frame):
	print( "Ctrl-C pressed. Terminating running players and exit")
	term_running()
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print( "serial-media-srv version {} starting {} ...".format(version, datetime.datetime.now()))

port = serial.Serial(serial_device, baudrate=57600, timeout=10003.0)

print( "serial port {} initilized".format(serial_device))

# reference to omx player
player = None
# reference to fim image player
fim = None

rx = re.compile( r'[0-9]+\.(jpg|png)$' )
images = {}
# generate dictionary for images
for i in filter(rx.search, os.listdir(basedir)):
    images[int(i[:i.index('.')])] = i

# generate dictionary for defaultimages
rx = re.compile( r'default.*\.(jpg|png)$' )
defaultimages = {}
k = 0
for i in filter(rx.search, os.listdir(basedir)):
    defaultimages[k] = i
    k += 1

rx = re.compile( r'[0-9]+\.(mp4|3gp|mov|avi)$' )
movies = {}
# generate dictionary for movies
for i in filter(rx.search, os.listdir(basedir)):
    movies[int(i[:i.index('.')])] = i

# generate dictionary for defaultmovie
rx = re.compile( r'default.*\.(mp4|3gp|mov|avi)$' )
defaultmovies = {}
k = 0
for i in filter(rx.search, os.listdir(basedir)):
    defaultmovies[k] = i
    k += 1

print( "images found: {}".format( images ))
print( "movies found: {}".format( movies ))
print( "defaultimages found: {}".format( defaultimages ))
print( "defaultmovies found: {}".format( defaultmovies ))
movie_playing = 0

def term_running():
    global player
    global fim
    if player is not None:
        player.quit()
        player = None
    if fim is not None:
        fim.terminate()
        fim = None
    return

def movie_ended():
    global movie_playing
    movie_playing = 0
    check_for_defaults()

def play_movie(id, m):
    global player, movie_playing
    print( "playing movie {}".format(m[id]))
    movie_playing = id
    player = OMXPlayer( Path(m[id]) )
    player.stopEvent += lambda _: movie_ended()

def show_image(id, m):
    global fim
    print( "showing image {}".format(m[id]))
    fim = subprocess.Popen("fim -a -q " + m[id], shell = True)

def check_for_defaults():
    global defaultmovies
    global defaultimages
    if len(defaultmovies) > 0:
        id = random.randint(0,len(defaultmovies)-1)
        play_movie(id, defaultmovies)
    if len(defaultimages) > 0:
        id = random.randint(0,len(defaultimages)-1)
        show_image(id, defaultimages)


# main loop
check_for_defaults()
while True:
    device = port.read()
    event =  port.read()
    if len(device)==0 or len(event)==0: continue
    id = ord(device) * 256 + ord(event)
    print( "Event received: {}:{} = {}". format(device,event,id) )
    #exit()
    if id == 0:
        term_running()
        check_for_defaults()
        continue
    if id in images:
        term_running()
        show_image(id, images)
    if id in movies and movie_playing != id:
        term_running()
        play_movie(id, movies)
