import numpy as np
import matplotlib.pyplot as plt
import glob
import os

dir = os.path.expanduser('~') + '/data/day2/'
data_files = sorted(glob.glob(dir + '*dat'))
meta_files = sorted(glob.glob(dir + '*metadata.npz'))

meta = np.load(meta_files[0])
d = np.fromfile(data_files[0], dtype=np.float32)
d = d.reshape(d.size / meta['vector_length'], meta['vector_length'])

# Make waterfall for given cfreq for full night
cfreq = 50e6
d = []
t = []
for mf, df in zip(meta_files, data_files):
	m = np.load(mf)
	if m['frequency'] != cfreq:
		continue
	t.append(m['times'][0])
	dtemp = np.fromfile(df, dtype=np.float32)
	d.append(dtemp.reshape(dtemp.size / m['vector_length'],
						   m['vector_length']))


# Make a waterfall by averaging each scan
d = []
for mf, df in zip(meta_files, data_files):
	m = np.load(mf)
	dtemp = np.fromfile(df, dtype=np.float32)
	dtemp = dtemp.reshape(dtemp.size / m['vector_length'],
						  m['vector_length'])
	d.append(np.mean(dtemp, axis=0))
	
# break into even and odd frequency tunings
d = np.array(d).reshape(48, 100, 1024)
# Flag center channels
d[:, :, 511:514] = 0.0

d0 = d[:, ::2, :].reshape(48, -1)
d1 = d[:, 1::2, :].reshape(48, -1)

