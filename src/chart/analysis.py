import numpy as np
import matplotlib.pyplot as plt
import os
import glob

# Read data file -> something useful
# Read metadata files
# averaging
# stacking
# combining frequencies into one spectrum ?


def print_meta(meta):
    for key in meta:
        if key == 'times':
            print('Number of time integrations:\t' + str(len(meta[key])))
        else:
            print(key, ':\t', meta[key])

def read_data(datafile, metadata_file, verbose=False):
    meta = np.load(meta_file)
    data = np.fromfile(datafile, dtype=meta['dtype'][0])
    data = data.reshape(data.size // meta['vector_length'], meta['vector_length'])
    if verbose:
        print_meta(meta)
    return data, meta


def plot_spectrum(data, meta):
    spectrum = np.average(data, axis=0)
    frequencies = ((np.arange(meta['vector_length']) - meta['vector_length'] / 2)
                   * meta['samp_rate'] / meta['vector_length'] + meta['frequency'])
    plt.plot(1e-6 * frequencies, spectrum)
    plt.xlabel('Frequency [MHz]')
    plt.ylabel('Power [Arb. Units]')


def find_dat_files(directory=None):
    if directory is None:
        directory = os.curdir()
    data_list = sorted(glob.glob(os.path.join(directory, '*.dat')))
    return data_list


def concat(data_list):
    raise NotImplementedError()
