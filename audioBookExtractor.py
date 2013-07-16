#! /usr/bin/env python

import os, sys, subprocess, argparse, time

parser = argparse.ArgumentParser(description='Audiobook Extractor.', epilog='Range or disc must be present.')
parser.add_argument('-c', '--cdopt', help="cdda2wav options. For example -c '-S 24' to run cdda2wav cd reading at 24x speed.")
parser.add_argument('-auto', '--auto', action='store_true', help="If present it will automatically open the cd tray and immediately begin trying to rip the next disk waiting for a cd to be put in the drive.")
parser.add_argument('-r', '--range', nargs=2, type=int, help='The start and ending disc numbers.')
parser.add_argument('-d', '--disc', type=int, help='disc number.')
parser.add_argument('-a', '--artist', help='artist name')
parser.add_argument('-s', '--sound', default='/System/Library/Sounds/Glass.aiff', help='A sound to play after a disc has been completed.')
parser.add_argument('-o', '--directory', help='Output directory for the files. Defaults to the album name.')
parser.add_argument('album', help='album name')

args = vars(parser.parse_args())

#clear our env variables that causes diskutil to complain
os.unsetenv("DYLD_LIBRARY_PATH")

#check if we have a cdda2wav options
if (args['cdopt'] != None):
	cdda2wavOptions = args['cdopt'] 
else:
	cdda2wavOptions = ''

album = args['album'] 

if (args['directory'] != None):
	output_dir = args['directory']
else:
	output_dir = album

print "output_dir: "+str(output_dir)
os.system("mkdir -p '"+output_dir+"'") 

artist = args['artist']

if (args['range'] != None):
	disc_start = args['range'][0] 
	disc_end = args['range'][1]
elif (args['disc'] != None):
	disc_start = args['disc']
	disc_end = args['disc']
else:
	parser.print_help()
	print "Missing range or disc argument."
	sys.exit(1)

auto = args["auto"] != None

#check to see if we have lame and cdda2wav
lame_check = os.system('which -s lame')
cdda2wav_check = os.system('which -s cdda2wav')

if (lame_check != 0):
	print "lame not installed...trying to install with brew"
	os.system('brew install lame')

if (cdda2wav_check != 0):
	print "cdda2wav not installed...trying to install with brew"
	os.system('brew install dvdrtools')

lame_check = os.system('which -s lame')
cdda2wav_check = os.system('which -s cdda2wav')

if (lame_check != 0):
	print "lame still not installed...exiting"
	sys.exit(1)

if (cdda2wav_check != 0):
	print "cdda2wav still not installed...exiting"
	sys.exit(1)

def checkForCD():
	#find which device is the cdrom drive
	disks = subprocess.check_output(["diskutil", "list"]).split("\n")

	cdDevice = None
	lastDevice = None
	for line in disks:
		if (line.startswith("/dev")):
			lastDevice = line
		else:
			if ('CD_partition_scheme' in line):
				cdDevice = lastDevice
				break # we found the cd device
	return cdDevice

def getIDForCD(cdDevice):
	#Get the disc id
	os.system("diskutil umountDisk "+cdDevice)
	info = subprocess.check_output(["cdda2wav","-D", "IODVDServices", "-J", "-g", "-v", "toc"], stderr=subprocess.STDOUT).split("\n")

	cdDevice = None
	lastDevice = None
	for line in info:
		if (line.startswith("CDINDEX discid:")):
			return line[16:]			

def waitForCD(max_tries = 1000, exit = True):
	print "Waiting for disc...",
	sys.stdout.flush()

	for i in range(1, max_tries+1):
		cdDevice = checkForCD()
		if (cdDevice != None):
			print ''
			return cdDevice
		time.sleep(1)
		print str(i),
		sys.stdout.flush()

	if exit:
		print ""
		print "CD Device not found."
		sys.exit(1)
	else:
		return False

def ejectDisc():
	os.system("drutil eject")

previousDiscs = {}

for disc in range(disc_start, disc_end+1):

	reader = 'cdda2wav'
	#reader = 'cdparanoia'
	title = album+" - Disc "+str(disc);
	output_file = title+".mp3"
	if (output_dir != None):
		output_file = output_dir + '/' + output_file

	print ""
	print "Ripping '"+output_file+"'"
	print ""

	if (artist != None):
		lameArtist = "--ta '"+str(artist)+"'"
	else:
		lameArtist = ''

	lameCmd = "lame --cbr -h -b 64 -m m --tn "+str(disc)+" --tl '"+album+"' --tt '"+title+"' "+lameArtist+"  - '"+output_file+"'"

	discReady = False
	while (discReady == False):
		if not auto:
			raw_input("Insert disc "+str(disc)+" and press ENTER")
			cdDevice = waitForCD()
		else:
			cdDevice = False
			while cdDevice == False:
				cdDevice = waitForCD(exit = False)

		discID = getIDForCD(cdDevice)
		print "discid: "+str(discID)
		if discID in previousDiscs:
			print "This looks like the same CD as disc "+str(previousDiscs[discID])+" but disc "+str(disc)+" is needed."
			print "Press ENTER to put in the correct CD or type \"F<ENTER>\" to force ripping of this disc..."
			action = raw_input()
			if action == "F":
				discReady = True
			else:
				ejectDisc()
		else:
			discReady = True
	
	previousDiscs[discID] = disc
	
	print "Ripping from device: "+cdDevice

	#os.system("growlnotify -t 'Start ripping.' -m 'Starting: "+title+"'")

	commands = []
	if reader == 'cdda2wav':
		commands.append("diskutil umountDisk "+cdDevice)
		commands.append("cdda2wav -D IODVDServices "+cdda2wavOptions+" -t all - | "+lameCmd)
	elif reader == 'cdparanoia':
		commands.append("cdparanoia -w '1-' - | "+lameCmd)

	for cmd in commands:
		print cmd
		os.system(cmd) 

	if (args['sound'] != None):
		os.system("afplay "+args['sound'])

	ejectDisc()

	#os.system("growlnotify -s -t 'Finished ripping.' -m 'Finished: "+title+"'")

	print "Finished disc "+str(disc)+" of "+str(disc_end)


print "Finished  "+title
