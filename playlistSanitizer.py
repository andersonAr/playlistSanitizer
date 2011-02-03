#!/usr/bin/python2.6
#
#    playlistSanitizer.py - Scans lyrics on iPOD playlists making sanitized versions
#    Copyright (C) 2010-2011  Armand Anderson <MrandersonAr at NOSPAMgmail DOT com> 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# DESCRIPTION
# Application for scanning songs on an ipod playlist for lyrics containing
# certain words. Suitable for fetching lyrics and scanning them for explicit
# lyrics.
#
# Currently uses lyricfly lyric database. Ipod support is provided by gpod
# library and supported models are limited by what gpod supports.
#
# Licenced under the Gnu General Public Licence, version 3
#
# To make my software work, you must use libgpod, which is available under 
# the Lesser GPL. Development and testing was completed with libgpod 0.7.95-1
#

import os, os.path
import gpod
import sys
import urllib2
import time
import getopt
import logging

def usage():
    print sys.argv[0] , "-l -n -v -p [playlist]"
    print "\tplaylistSanitizer.py -l --list-playlists"
    print "\tplaylistSanitizer.py -n --no-write  Do not write chnages to iPod"
    print "\tplaylistSanitizer.py -v --verbose   Print verbose output to screen"
    print "\tplaylistSanitizer.py -p [playlist]  Sanitize (copy of) playlist"

def get_playlists(playlists):
    ret = True

    if playlists is None:
         playlists = []

    for playlist in gpod.sw_get_playlists(itdb):
        playlists.append(playlist)

    return ret 

def explicit_count(track):
    ret = 0
    sResultArtist =  ""
    sResultTitle = ""
    sResultAlbum = ""
    sResultText = ""

    # Format for fetch is http://api.lyricsfly.com/api/api.php?i=963483002885003db-temporary.API.access&a=Led%Zepplin&t=Kashmir

    import re

    artist = str(track.artist)
    title = str(track.title)
    album = str(track.album)
    p = re.compile('\W')
    # Replace whitespace and non wrd characters with % for querying purposes
    artist=p.sub('%',artist)
    title=p.sub('%',title)

    lyricURL = "http://api.lyricsfly.com/api/api.php?i=" + lyric_key + "&a=" + artist + "&t=" + title
    log.info('Processing lyric result for ' + lyricURL)
    log.info("Track album is " + album)

    from xml.dom.minidom import parse, parseString

    #Fetch the page from lyricsfly
    f = urllib2.urlopen(lyricURL)
    
    # Need to do this in order to have variables constructed for loop
    # TODO clean this up so code isn't redundant with loop below
    result=f.read() 
    dom = parseString(result) 
    sResultStatus = dom.getElementsByTagName('status')[0] 
    delay = 5 # set default delay to be 5

    while sResultStatus.childNodes[0].data == '402':
        # Parse out delay value returned by lyric service and sleep that long 
	# before querying again
        delay = int(dom.getElementsByTagName('delay')[0].childNodes[0].data) 
	delay = (delay)/1000
	log.warn( 'Recieved query too rapidly error sleeping for ' + \
            str(delay) + ' seconds')
        time.sleep(delay)
        f = urllib2.urlopen(lyricURL)
        result=f.read()
        # Populate our DOM object
        dom = parseString(result)   
        log.info( " Result is :\n" + dom.toprettyxml())
        # Iterate through matches
        sResultStatus = dom.getElementsByTagName('status')[0]
        log.info('sResultStatus is ' , sResultStatus.childNodes[0].data) 

    #If no results or other failure return -1  
    if sResultStatus.childNodes[0].data == '204':
        return -1

    elif sResultStatus.childNodes[0].data == '401':
        log.error(" Recieved unauthorized error on lyric lookup. Maybe key " +
            "is bad")
        sys.exit()

    #At this point we should have valid results and need to iterate through them
    #TODO Build some logic for best match (for example: compare Album Name to our track's album name )
    #TODO Case to properly identify lyrics for various versions of song Radio edit versus regular
    matchInstance=0
    for songResult in dom.getElementsByTagName('sg'):
        matchInstance+=1
        setVals = False
        for tag in [ "ar" , "tt" , "tx", "al" ]:
            log.info("Processing element " + tag)
            if  songResult.getElementsByTagName(tag).item(0).hasChildNodes \
                    and songResult.getElementsByTagName(tag).item(0).\
                        childNodes.length > 0:   
                tagResult = songResult.getElementsByTagName(tag).item(0). \
                    childNodes.item(0).data 
                if (tag == 'al' and tagResult == album) or matchInstance ==1:
                    setVals=True
 
                if tag == "ar" and setVals: sResultArtist = tagResult
                elif tag == "tt"and setVals: sResultTitle = tagResult
                elif tag == "al" and setVals: sResultAlbum = tagResult
                elif tag == "tx" and setVals: sResultText = tagResult
    log.info( 'Song, Title: ' + sResultArtist + ' - ' + sResultTitle)
    log.info('Album: ' + sResultAlbum)
    log.info('Text: ' + sResultText)

    p = re.compile('fuck|shit|hell|damn|goddamn|ass|bitch|whore')
    matchList = re.findall(p,sResultText)   
    ret = len(matchList) 

    #This helps us avoid back to back queries too rapid while iterating through playlist
    #TODO something smarter probably in main, might need to pass back delay value from API service
    log.info('Sleeping inside a single use function, this is probably not ideal')
    time.sleep(delay)

    return ret

# Main:

explicitThreshold = 1    #how much badness we'll allow per song
writeChanges = False
verbose = False
listPlaylists = False
noWrite = False
playlistSelected = ""

log = logging.getLogger('My Logger')
# Logging configuration, to stdout in this case
console = logging.StreamHandler()
log.addHandler(console)
log.setLevel(logging.WARNING)

# Get command line options and args
try:
    opts, args = getopt.getopt(sys.argv[1:], 'vnlp:', ["help", "no-write" ,"verbose", "list-playlists", "playlist="])
except getopt.GetoptError, err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

for o, a, in opts:
    if o in ("-v", "--verbose"):
        verbose = True
        log.setLevel(logging.INFO)
    elif o in ("-n","--no-write"):
        noWrite = True
    elif o in ("-l", "--list-playlists"):
        listPlaylists = True
    elif o in ("-p", "--playlist"):
        playlistSelected = a
        log.info("Playlist selected = " + playlistSelected)
    else:
        assert False, "unhandled option"

if listPlaylists and len(playlistSelected)>0:
    log.error("List Playlist and Platlist selection options are mutually exclusive")
    usage()
    sys.exit()

ipod_mount = '/media/IPOD'

# lyrics fly - new key @ http://lyricsfly.com/api/
lyric_key= "3a80056cc9a51c3a8-temporary.API.access"  #key for lyric API
log.warn("Using temporary key... FULL LYRICS WILL NOT BE SCANNED - testing only")

dbname = os.path.join(ipod_mount,"iPod_Control/iTunes/iTunesDB")

itdb = gpod.itdb_parse(ipod_mount, None)
if not itdb:
    print "Failed to read %s" % dbname
    sys.exit(2)
itdb.mountpoint = ipod_mount

playlists = []

get_playlists(playlists)

for playlist in playlists:
    
    if (listPlaylists or verbose):
        print "Playlist Name: " , playlist.name  #  , "Type: ", type(playlist.name)
  
    #import pdb; pdb.set_trace() 
    if playlistSelected != playlist.name: continue 

    if playlistSelected:
        print "test check for new playlist construction" 
        #Create our temp playlist and start putting tracks in it that meet our clean threshold 
        tmpPlaylistName = "Clean."+playlist.name
        tmpPlaylist = gpod.itdb_playlist_new(tmpPlaylistName, 0)
        gpod.itdb_playlist_add(itdb,tmpPlaylist,-1)

    if listPlaylists == False:
        #iterating over tracks on ipod (didn't pass the object representing tracks)
        for track in gpod.sw_get_playlist_tracks(playlist):
            print track.artist, "-" ,track.title
            explicitCount = explicit_count(track)
            print 'Explicit Count is: ' , explicitCount
            if explicitCount <= explicitThreshold and  \
                explicitCount >= 0:   #if this track is a keeper
		#Add our track to our already constructed playlist
                gpod.itdb_playlist_add_track(tmpPlaylist,track, -1)
            # TODO REMOVE THIS - this is JUST FOR TESTING
            #if track.title == "Some Song Title To Break On":
            #    print "***********BREAKING FOR TEST PURPOSES************"
            #    break

    if len(gpod.sw_get_playlist_tracks(tmpPlaylist)) > 0:
        log.warn("Writing a new clean playlist")
        log.warn("Created playlist \"" + tmpPlaylistName + "\" with " + str(len(gpod.sw_get_playlist_tracks(tmpPlaylist))) + " tracks")
        writeChanges = True

if writeChanges == False:
    print "No Changes to write"
elif noWrite:
    log.warn("NOT writing itdb (--no-write set)")
else:
    gpod.itdb_write(itdb, None)
    
