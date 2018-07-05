import os
import re
import serial
import subprocess
import sys

from pathlib import Path
from omxplayer.player import OMXPlayer

port = serial.Serial("/dev/ttyS0", baudrate=115200, timeout=10003.0)
# reference to omx player
player = None
# reference to fim image player
fim = None

basedir = '.'
if len(sys.argv) > 1:
    basedir = sys.argv[1]

rx = re.compile( r'\.(jpg|png)' )
images = {}
# generate dictionary for images
for i in filter(rx.search, os.listdir(basedir)):
    images[i[:i.index('.')]] = i

rx = re.compile( r'\.(mp4|3gp|mov)' )
movies = {}
# generate dictionary for movies
for i in filter(rx.search, os.listdir(basedir)):
    movies[i[:i.index('.')]] = i

print( "images found: {}".format( images ))
print( "movies found: {}".format( movies ))

def term_running():
    if player is not None:
        player.quit()
        player = None
    if fim is not None:
        fim.terminate()
        fim = None
    return

# main loop
while True:
    device = port.read()
    event =  port.read()
    if len(device)==0 or len(event)==0: continue
    id = ord(device) * 256 + ord(event)
    print( "Event received: {}:{}". format(device,event) )
    if id == 0:
        term_running()
        continue
    if id in images:
        term_running()
        print( "showing image {}".format(images[id]))
        fim = subprocess.Popen("fim -a -q " + images[id], shell = True)
    if id in movies:
        term_running()
        print( "playing movie {}".format(movies[id]))
        player = OMXPlayer( Path(movies[id]) )
