import os
import sys
import time
import gps

try:
	gpsd = gps.gps(mode=gps.WATCH_ENABLE)
except:
	print('ERROR: No GPS Present, time not set!!")
	sys.exit()

while True:
	gpsd.next()
	utc = gpsd.utc
	if utc != None and utc != '':
		# native format: '2015-04-01T17:32:04.000Z'
		# need format: '20150401 17:32:04'
		gpsutc = utc[0:4] + utc[5:7] + utc[8:10] + ' ' + utc[11:19]
		os.system('sudo date -u --set=' + gpsutc)
		sys.exit

