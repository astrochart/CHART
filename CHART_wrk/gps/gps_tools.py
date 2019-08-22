import os
import sys
import time
import gps


def set_time(timeout_interval=60., sleep_interval=1):

	t0 = time.time()
	while time.time() < t0 + timeout_interval:
		try:
			gpsd = gps.gps(mode=gps.WATCH_ENABLE)
		except:
			# No GPS present, sleep then try again
			time.sleep(sleep_interval)
			if time.time() >= t0 + timeout_interval:
				raise ValueError('No GPS present, time not set.')
			else:
				continue

	while time.time() < t0 + timeout_interval:
		gpsd.next()
		utc = gpsd.utc
		if utc != None and utc != '':
			# native format: '2015-04-01T17:32:04.000Z'
			# need format: '20150401 17:32:04'
			gpsutc = utc[0:4] + utc[5:7] + utc[8:10] + ' ' + utc[11:19]
			os.system('sudo date -u --set=' + gpsutc)
			return
	# If we've made it to this line, we exceeded the time
	# interval without getting a fix.
	raise ValueError('No GPS fix, time not set.')


def monitor():
	# Listen on port 2947 (gpsd) of localhost
	session = gps.gps('localhost', '2947')
	session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

	while True:
		try:
		    report = session.next()
		    print('\n')
		    print(report)
		    if report['class'] == 'TPV':
		        if hasattr(report, 'time'):
		            print(report.time)
		except KeyError:
		    pass
		except KeyboardInterrupt:
		    quit()
		except StopIteration:
		    session = None
		    print('GPSD has terminated')

