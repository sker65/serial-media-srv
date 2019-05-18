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
from subprocess import TimeoutExpired
from subprocess import PIPE
import sys
import random
import signal
import datetime
import threading
from shutil import copyfile
import configparser
import logging
from time import sleep

from pathlib import Path
#from omxplayer.player import OMXPlayer

config = configparser.ConfigParser()
# defaults
config['general']={}
config['general']['device']='/dev/ttyS0'
config['general']['baud'] = '57600'
config['general']['timeout'] = '100000'
config['player']={}
config['player']['exec'] = 'omxplayer -b'
config['viewer']={}
config['viewer']['exec'] = 'fim -a -q'
config['slide']={}
config['slide']['exec'] = "fim -a -q -c 'while(1){display;sleep\"5\";next;}'"

config.read('serial-media-srv.ini')

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('serial-media-server')

# refresh start.sh itself if necessary
newStart = Path("./new-start.sh")
if newStart.is_file():
    copyfile("./new-start.sh", "./start.sh")
    newStart.unlink()

version = '1.0.4'

basedir = '.'
if len(sys.argv) > 1:
    basedir = sys.argv[1]

serial_device = config['general']['device']
if len(sys.argv) > 2:
    serial_device = sys.argv[2]

def signal_handler(sig, frame):
    global log
    log.info( "Ctrl-C pressed. Terminating running players and exit")
    term_running()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
readFromFile = ''

log.info( "serial-media-srv version {} starting ...".format(version ))
if config.has_option('general', 'readFrom'):
    readFromFile = config['general']['readFrom']

baud=int(config['general']['baud'])

if len(readFromFile)==0:
    port = serial.Serial(serial_device, baudrate=baud, timeout=int(config['general']['timeout']))
    log.info( "serial port {} initilized with {}".format(serial_device, baud))
else:
    file = open( readFromFile, "r")

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
processes = {}
follow_task = 0

class Task(object):
    def __init__(self, type, id, proc):
        self.type = type
        self.proc = proc
        self.playing = id

def onProcessExit(task):
    global processes, follow_task
    log.info("player process {} playing {} exited".format(task.proc.pid, task.playing))
    del processes[task.proc.pid]
    if len(processes) == 0 and follow_task == 0: check_for_defaults()

def onFimProcessExit(task):
    global processes
    log.info("fim process {} showing {} exited".format(task.proc.pid, task.playing))
    del processes[task.proc.pid]

def popenAndCall(onExit, type, id, *popenArgs, **popenKWArgs):
    global processes
    proc = Popen(*popenArgs, **popenKWArgs)
    task = Task(type,id,proc)
    def runInThread(onExit, proc):
        proc.wait()
        onExit(task)
        return
    thread = threading.Thread(target=runInThread, args=(onExit, proc))
    processes[proc.pid] = task
    thread.start()
    return proc # returns immediately after the thread starts

def term_running():
    global processes
    for pid in list(processes):
        task = processes[pid]
        log.debug("ending task {}".format(pid))
        if task.type == 1:
            try:
                outs, errs = task.proc.communicate(input="q".encode('utf-8'),timeout=1)
            except TimeoutExpired:
                task.proc.kill()
            if task.proc is not None: task.proc.send_signal(signal.SIGINT)
        if task.type == 2:
            task.proc.send_signal(signal.SIGINT)
            task.proc.kill()

def play_movie(name):
    global movie_playing, config, log
    movie_playing = name
    args = config['player']['exec'].split()
    args.append( Path(name).absolute().as_posix() )
    log.debug("running: {}".format(args))
    player = popenAndCall(onProcessExit, 1, name, args, stdin=PIPE, stdout=PIPE, shell=False )
    #player = Popen(['omxplayer', '-b', Path(m[id]).absolute().as_posix() ], stdin=PIPE, stdout=PIPE, shell=False  )
    log.debug( "playing movie {} in process {}".format(name,player.pid))
    #player.set_aspect_mode(config['player'].get('aspectMode','stretch'))
    #player.stopEvent += lambda _: movie_ended()

def show_image(name):
    global log
    log.debug( "showing image '{}'".format(name))
    args = config['viewer']['exec'].split()
    args.append( Path(name).absolute().as_posix() )
    log.debug("running: {}".format(args))
    fim = popenAndCall(onFimProcessExit, 2, name, args, stdin=PIPE, stdout=PIPE, shell = False)
    log.debug( "started fbi process {}".format(fim.pid))

def run_slideshow(path_pattern):
    global log
    log.debug("running slideshow '{}'".format(path_pattern))
    args = config['slide']['exec'].split()
    args.append( path_pattern )
    log.debug("running: {}".format(args))
    fim = popenAndCall(onFimProcessExit, 2, name, args, stdin=PIPE, stdout=PIPE, shell = False)
    log.debug( "playing slide {} in process {}".format(name,player.pid))

def check_for_defaults():
    global defaultmovies, defaultimages, movie_playing
    if len(defaultmovies) > 0:
        id = random.randint(0,len(defaultmovies)-1)
        play_movie(defaultmovies[id])
    if len(defaultimages) > 0:
        id = random.randint(0,len(defaultimages)-1)
        movie_playing = None
        show_image(defaultimages[id])

def handleCmd( tokens ):
    global follow_task, log
    cmd = tokens[0]
    log.debug("handling cmd '{}' ntok {}".format(cmd,len(tokens)))
    if cmd == 'STOP':
        term_running()
        # not necessary on exit handler does it //check_for_defaults()
    elif cmd == 'PLAY' and len(tokens) > 1:
        media = tokens[1]
        if media.endswith('.png') or media.endswith('.jpg'):
            term_running()
            show_image(media)
        else: 
            if movie_playing != media:
                follow_task = 1
                term_running()
                play_movie(media)
            else:
                log.info("same movie already playing ({})".format(movie_playing))
    elif cmd == 'SLEEP' and len(tokens) > 1:
        sleep( int(tokens[1]) )
    elif cmd == 'SLIDE' and len(tokens) > 1:
        term_running()
        run_slideshow( tokens[1] )
    elif cmd == 'PLAYONEOF' and len(tokens) > 1:
        media = tokens[1:]
        # choose one
        i = random.randint(0,len(media)-1)
        movie = media[i]
        if movie != movie_playing:
            follow_task = 1
            term_running()
            play_movie(movie)
        else:
            log.info("same movie already playing ({})".format(movie_playing))


def readNextLine():
    global readFromFile, file
    if not readFromFile:
        r = port.readline().strip().decode('ISO-8859-1')
        log.debug("got line '{}'".format(r))
        return r
    else:
        r = file.readline()
        return r

# main loop
check_for_defaults()
while True:
    follow_task = 0
    line = readNextLine()
    if len(line) == 0:
        continue
    tokens = line.split()
    if len(tokens) == 0:
        continue
    try:
        handleCmd( tokens )
    except:
        continue    
