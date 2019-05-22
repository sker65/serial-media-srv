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
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from urllib.parse import parse_qs
import mimetypes
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
config['general']['httpport'] = '31009'
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

version = '1.0.5'
httpd = None
file = None
port = None
connection = None
current_connection = None

# where the python script is running
mydir = os.path.dirname(os.path.realpath(__file__))
basedir = '.'
shouldRun = True

if len(sys.argv) > 1:
    basedir = sys.argv[1]

serial_device = config['general']['device']
if len(sys.argv) > 2:
    serial_device = sys.argv[2]

def term_and_exit():
    global log, httpd, shouldRun
    shouldRun = False
    log.info( "Terminating running players and exit")
    term_running()
    if current_connection:
        current_connection.close()
    if connection:
        connection.close()
    if port:
        port.close()
    if httpd:
        httpd.shutdown()
    sys.exit(0)

def signal_handler(sig, frame):
    global log
    log.info( "Ctrl-C pressed.")
    term_and_exit()

signal.signal(signal.SIGINT, signal_handler)

log.info( "serial-media-srv version {} starting ...".format(version ))
log.debug("Running in %s" % mydir)

baud=int(config['general']['baud'])

if config.has_option('general', 'socketport'):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sport=int( config['general']['socketport'])
    connection.bind(('0.0.0.0', sport))
    log.debug("listening for cmd on {}".format(sport))
    connection.listen(10)
elif config.has_option('general', 'readFrom'):
    file = open( config['general']['readFrom'], "r")
    log.debug("reading from file {}".format(config['general']['readFrom']))
else:
    port = serial.Serial(serial_device, baudrate=baud, timeout=int(config['general']['timeout']))
    log.info( "serial port {} initilized with {}".format(serial_device, baud))   

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

movies = {}

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
    global movie_playing, config, log, current_connection
    media = Path(name).absolute()
    movie_playing = name
    args = config['player']['exec'].split()
    args.append( media.as_posix() )
    log.debug("running: {}".format(args))
    player = popenAndCall(onProcessExit, 1, name, args, stdin=PIPE, stdout=PIPE, shell=False )
    #player = Popen(['omxplayer', '-b', Path(m[id]).absolute().as_posix() ], stdin=PIPE, stdout=PIPE, shell=False  )
    log.debug( "playing movie {} in process {}".format(name,player.pid))
    #player.set_aspect_mode(config['player'].get('aspectMode','stretch'))
    #player.stopEvent += lambda _: movie_ended()
    if current_connection:
        current_connection.send("# playing {}\r\n".format(name).encode(charset))

def show_image(name):
    global log
    log.debug( "showing image '{}'".format(name))
    args = config['viewer']['exec'].split()
    args.append( Path(name).absolute().as_posix() )
    log.debug("running: {}".format(args))
    fim = popenAndCall(onFimProcessExit, 2, name, args, stdin=PIPE, stdout=PIPE, shell = False)
    log.debug( "started fbi process {}".format(fim.pid))
    if current_connection:
        current_connection.send("# playing {}\r\n".format(name).encode(charset))

def run_slideshow(name):
    global log
    log.debug("running slideshow '{}'".format(name))
    args = config['slide']['exec'].split()
    args.append( name )
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
    cmd = tokens[0].upper()
    log.debug("handling cmd '{}' args {}".format(cmd,tokens[1:]))
    if cmd == 'STOP':
        term_running()
        # not necessary on exit handler does it //check_for_defaults()
        return 0
    elif cmd == 'PLAY' and len(tokens) > 1:
        media = tokens[1]
        if Path(media).is_file():
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
            return 0
        else:
            log.error("media not found '{}'".format(media))
            if current_connection:
                current_connection.send("# media not found '{}'\r\n".format(media).encode(charset))
            return 1

    elif cmd == 'SLEEP' and len(tokens) > 1:
        sleep( int(tokens[1]) )
        return 0
    elif cmd == 'SLIDE' and len(tokens) > 1:
        term_running()
        run_slideshow( tokens[1] )
    elif cmd == 'PLAYONEOF' and len(tokens) > 1:
        media = tokens[1:]
        # choose one
        i = random.randint(0,len(media)-1)
        movie = media[i]
        if Path(movie).is_file():       
            if movie != movie_playing:
                follow_task = 1
                term_running()
                play_movie(movie)
            else:
                log.info("same movie already playing ({})".format(movie_playing))
            return 0
        else:
            log.error("media not found '{}'".format(movie))
            return 1
    else:
        log.error("unknown command" )
        return 2

def term_with_delay():
    sleep(5)
    term_and_exit()

# HTTPRequestHandler class
class testHTTPServer_RequestHandler(BaseHTTPRequestHandler):
    global version,log

    def log_message(self, format, *args):
        log.info("http access - %s - - [%s] %s" %
                        (self.client_address[0],
                        self.log_date_time_string(),
                        format%args))

    def sendJsonResponse( self, message ):
        self.send_response(200)
        self.send_header('Content-type','application/json')
        self.end_headers()
        self.wfile.write(bytes(message, "utf8"))
        return

    def sendFile(self, realpath):
        addEncodingHeader = False
        try:
            filepath = realpath
            if os.path.isfile(realpath+'.gz'):
                filepath = realpath + '.gz'
                addEncodingHeader = True
            # print ( realpath )
            f = open(filepath, "rb")

        except IOError:
            self.send_error(404,'File Not Found: %s ' % realpath)

        else:
            self.send_response(200)
            #this part handles the mimetypes for you.
            mimetype, _ = mimetypes.guess_type(realpath)
            self.send_header('Content-Type', mimetype)
            if addEncodingHeader:
                self.send_header('Content-Encoding', 'gzip')
            self.end_headers()
            for s in f:
                self.wfile.write(s)
            return

    # GET
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == '/restart':
            thread = threading.Thread(target=term_with_delay)
            thread.start()
            self.sendJsonResponse('{ "result": "success", "message": "server is restaring. Hold on" }' )
            return

        if url.path == '/log':
            realpath = os.path.join('.', 'serial.log')
            self.sendFile(realpath)
            return
        if url.path == '/version':
            self.sendJsonResponse('{ "version": "%s" }' % (version))
            return
        if url.path == '/cmd':
            qs = parse_qs( url.query )
            if 'c' in qs:
                cmd = qs['c'][0]
                try:
                    r = handleCmd(cmd.split())
                except:
                    log.error("Oops! "+sys.exc_info()[0]+" occured.")
                
                if r == 0:
                    self.sendJsonResponse('{ "result": "success", "message": "%s" }' % (cmd))
                else:
                    self.sendJsonResponse('{ "result": "error", "message": "code %d" }' % (r))
            else:
                self.sendJsonResponse('{ "result": "error", "message": "code %d" }' % (3))
            return

        if self.path in ("", "/"):
            filepath = "index.html"
        else:
            filepath = self.path.lstrip("/")
        realpath = os.path.join(mydir+'/html', filepath)
        self.sendFile(realpath)

def run_httpservice():
    global httpd, log, config
    log.debug('starting http server...')
    httpport=int(config['general']['httpport'])
    # Server settings
    server_address = ('', httpport)
    httpd = HTTPServer(server_address, testHTTPServer_RequestHandler)
    log.debug("running http server on port {} ...".format(httpport))
    httpd.serve_forever()

if config.has_option('general', 'httpport'):
    thread = threading.Thread(target=run_httpservice)
    thread.start()

charset = 'ISO-8859-1'

def readNextLine():
    global port, file, current_connection
    if connection:
        r = current_connection.recv(2048)
        if not r:
            current_connection = None
            return None
        r = r.strip().decode(charset)
        log.debug("got line '{}'".format(r))
        return r
    elif port:
        r = port.readline().strip().decode(charset)
        log.debug("got line '{}'".format(r))
        return r
    elif file:
        r = file.readline()
        return r
    else:
        log.error("No input device")

# main loop
check_for_defaults()
while shouldRun:
    if connection:
        log.debug("waiting for connection")
        current_connection, address = connection.accept()
        log.debug("client connected from {}".format(address))
        current_connection.send("# serial-media-server {}\r\n".format(version).encode(charset))
    while shouldRun:
        follow_task = 0
        line = readNextLine()
        if not line:
            break
        if len(line) == 0:
            continue
        tokens = line.split()
        if len(tokens) == 0:
            continue
        try:
            handleCmd( tokens )
        except:
            log.error("Oops! "+sys.exc_info()[0]+" occured.")
            continue
