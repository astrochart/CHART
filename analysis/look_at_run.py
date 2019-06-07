import numpy as np
import matplotlib.pyplot as plt
import glob
import os

path = os.path.expanduser('~') + '/data/day2/'
data_files = sorted(glob.glob(path + '*dat'))
meta_files = sorted(glob.glob(path + '*metadata.npz'))

meta = np.load(meta_files[0])
data = np.fromfile(data_files[0], dtype=np.float32)
data = data.reshape(data.size / meta['vector_length'], meta['vector_length'])

# Make waterfall for given cfreq for full night
cfreq = 50e6
data = []
time = []
for mf, df in zip(meta_files, data_files):
	meta = np.load(mf)
	if meta['frequency'] != cfreq:
		continue
	time.append(meta['times'][0])
	dtemp = np.fromfile(df, dtype=np.float32)
	data.append(dtemp.reshape(dtemp.size / meta['vector_length'],
						   meta['vector_length']))


# Make a waterfall by averaging each scan
data = []
for mf, df in zip(meta_files, data_files):
	meta = np.load(mf)
	dtemp = np.fromfile(df, dtype=np.float32)
	dtemp = dtemp.reshape(dtemp.size / meta['vector_length'],
						  meta['vector_length'])
	data.append(np.mean(dtemp, axis=0))
	
# break into even and odd frequency tunings
data = np.array(data).reshape(48, 100, 1024)
# Flag center channels
data[:, :, 511:514] = 0.0

data0 = data[:, ::2, :].reshape(48, -1)
data1 = data[:, 1::2, :].reshape(48, -1)

