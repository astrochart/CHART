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
    meta = np.load(metadata_file, allow_pickle=True)
    if 'dtype' in meta:
        data = np.fromfile(datafile, dtype=meta['dtype'][0])
    else:
        data = np.fromfile(datafile, dtype=np.float32)
    data = data.reshape(data.size // meta['vector_length'], meta['vector_length'])
    if verbose:
        print_meta(meta)
    return data, meta


def plot_spectrum(data, meta):
    spectrum = np.mean(data, axis=0)
    frequencies = ((np.arange(meta['vector_length']) - meta['vector_length'] / 2)
                   * meta['samp_rate'] / meta['vector_length'] + meta['frequency'])
    plt.plot(1e-6 * frequencies, spectrum)
    plt.xlabel('Frequency [MHz]')
    plt.ylabel('Power [Arb. Units]')
    

def find_dat_files(directory=None):
    if directory is None:
        directory = os.curdir()
    data_list = sorted(glob.glob(os.path.join(directory, '*.dat')))
    if len(data_list) == 0:
        raise FileNotFoundError('No data files found in directory: ' + directory)
    return data_list


def find_meta_files(directory=None):
    if directory is None:
        directory = os.curdir()
    meta_list = sorted(glob.glob(os.path.join(directory, '*.npz')))
    if len(meta_list) == 0:
        raise FileNotFoundError('No metadata files found in directory: ' + directory)
    return meta_list

def get_meta_param(prompt):
    res = input(prompt)
    if res == '':
        return None
    else:
        try:
            return float(res)
        except ValueError:
            print("Invalid input. Please enter a valid number.")
            return get_meta_param(prompt)


def read_run(directory=None, overwrite_v1=False):
    if directory is None:
        directory = os.curdir()
    data_list = find_dat_files(directory=directory)
    meta_list = find_meta_files(directory=directory)
    data = []
    meta = []
    # Check for old data format. Ask user for missing info. 
    # If not known, set to None
    metatemp = np.load(meta_list[0], allow_pickle=True)
    if 'azimuth' not in metatemp:
        version = 1
        print(f'CHART v1 data format in {directory}.')
        print('Please enter the missing information:')
        latitude = get_meta_param('Latitude [degrees]: ')
        longitude = get_meta_param('Longitude [degrees]: ')
        altitude = get_meta_param('Altitude [degrees]: ')
        azimuth = get_meta_param('Azimuth [degrees]: ')
        
        if overwrite_v1:
            print('Overwriting metadata files with new format...')
    else:
        version = 2
    for dfile, mfile in zip(data_list, meta_list):
        datatemp, metatemp = read_data(dfile, mfile)
        if version == 1:
            metatemp['azimuth'] = azimuth
            metatemp['altitude'] = altitude
            metatemp['latitude'] = latitude
            metatemp['longitude'] = longitude
            if overwrite_v1:
                np.savez(mfile, **metatemp)
        data.append(datatemp)
        meta.append(metatemp)
    return data, meta



def concat(data_list):
    raise NotImplementedError()
