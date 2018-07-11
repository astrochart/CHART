import numpy as np
import matplotlib.pyplot as plt
import os

def readdata(datafile):
	d = np.fromfile(datafile, dtype=np.float32)
	return d

def readarray(datafile):
	d = np.fromfile(datafile, dtype=np.float32)
	d = d.reshape(d.size/1024, 1024)
	return d

def avgplot(datafile):
	a=readarray(datafile)
	b = np.average(a, axis=0)
	plt.plot(b)
	return b

def wf_plot(datafile):
	a = readarray(datafile)
	plt.imshow(a)
	#print a.shape

def find_dat_files():
	items = os.listdir(".")
	dataList = []
	for names in items:
		if names.endswith('00rtldata.dat'):
			dataList.append(names)
	dataList.sort()
	return dataList

def concat(dataList):
	dataList = find_dat_files(dataList)
	combined = np.empty((100,0))
	for a in range(0, len(dataList)):
		combined = np.concatenate((combined, readarray(dataList[a])), 1)
	vmin=a.min()
	vmax=a.max()	
	plt.imshow(combined, norm=SymLogNorm(vmax=vmax, vmin=vmin,linthresh=1e2))
	return combined
