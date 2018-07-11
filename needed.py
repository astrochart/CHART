import numpy as np
import matplotlib.pyplot as plt

def readdata(datafile):
	d = np.fromfile(datafile, dtype=np.float32)
	return d

def avgplot(datafile):
	a=readdata(datafile)
	b = a.reshape(a.size/1024, 1024)
	c = np.average(b, axis=0)
	plt.plot(c)
	return c

def wf_plot(datafile):
	a = readdata(datafile)
	b = a.reshape(a.size/1024, 1024)
	plt.imshow(b)
	print b.shape
