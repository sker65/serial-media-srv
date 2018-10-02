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
from subprocess import Popen
from subprocess import PIPE
import sys
import random
import signal
import datetime
import threading
from shutil import copyfile
import configparser
import logging

from pathlib import Path
#from omxplayer.player import OMXPlayer

config = configparser.ConfigParser()
config['player']={}
config.read('serial-media-srv.ini')

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('serial-media-server')

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
    global log
    log.info( "Ctrl-C pressed. Terminating running players and exit")
    term_running()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

log.info( "serial-media-srv version {} starting ...".format(version ))

port = serial.Serial(serial_device, baudrate=57600, timeout=1000000)

log.info( "serial port {} initilized".format(serial_device))

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

log.info( "images found: {}".format( images ))
log.info( "movies found: {}".format( movies ))
log.info( "defaultimages found: {}".format( defaultimages ))
log.info( "defaultmovies found: {}".format( defaultmovies ))
movie_playing = 0

def onProcessExit(proc):
    log.info("player process {} exited".format(proc.pid))
    movie_ended()

def popenAndCall(onExit, *popenArgs, **popenKWArgs):
    proc = Popen(*popenArgs, **popenKWArgs)
    def runInThread(onExit, proc):
        proc.wait()
        onExit(proc)
        return
    thread = threading.Thread(target=runInThread, args=(onExit, proc))
    thread.start()
    return proc # returns immediately after the thread starts

def term_running():
    global player,fim
    if player is not None:
        log.debug("ending player process {}".format(player.pid))
        try:
            outs, errs = player.communicate(input="q".encode('utf-8'),timeout=1)
        except TimeoutExpired:
            player.kill()
        player.send_signal(signal.SIGINT)
        player = None
    if fim is not None:
        fim.send_signal(signal.SIGINT)
        fim.kill()
        fim = None
    return

def movie_ended():
    global movie_playing, log, player
    log.debug( "movie {} ended".format(movie_playing))
    movie_playing = 0
    player = None
    check_for_defaults()

def play_movie(id, m):
    global player, movie_playing, config, log
    log.debug( "playing movie {}".format(m[id]))
    movie_playing = id
    if player is not None: player.kill()
    player = popenAndCall(onProcessExit, ['omxplayer', '-b', Path(m[id]).absolute().as_posix() ], stdin=PIPE, stdout=PIPE, shell=False )
    #player = Popen(['omxplayer', '-b', Path(m[id]).absolute().as_posix() ], stdin=PIPE, stdout=PIPE, shell=False  )
    #player.set_aspect_mode(config['player'].get('aspectMode','stretch'))
    #player.stopEvent += lambda _: movie_ended()

def show_image(id, m):
    global fim, log
    log.debug( "showing image {}".format(m[id]))
    fim = Popen(['fim', '-a', '-q', m[id] ], stdin=PIPE, stdout=PIPE, shell = False)
    #fim = Popen(['fbi', '-a', '-d', '/dev/fb0', '-noverbose', m[id] ], stdin=PIPE, stdout=PIPE, shell = False)
    #outs, errs = fim.communicate(input="j".encode('utf-8'),timeout=1)
    log.debug( "started fbi process {}".format(fim.pid))

def check_for_defaults():
    global defaultmovies, defaultimages
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
    if len(device)==0 or len(event)==0:
        continue
    id = ord(device) * 256 + ord(event)
    log.debug( "Event received: {}:{} = {}". format(device,event,id) )
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
