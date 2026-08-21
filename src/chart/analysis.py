import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import time
from astropy import units as u
from astropy.coordinates import SpectralCoord, EarthLocation, SkyCoord, AltAz, ICRS
from astropy.time import Time
from ipywidgets import FloatSlider, Dropdown, HBox, VBox, widgets
from IPython.display import display
import scipy.constants as const

f_e = 1.420405751768 * u.GHz  # Rest frequency of HI hyperfine transition
speed_of_light = const.speed_of_light * (u.meter / u.second)
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

def get_utc_datetime(t):
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(t))

def read_data(datafile, metadata_file, verbose=False):
    meta = dict(np.load(metadata_file, allow_pickle=True))
    if 'dtype' in meta:
        data = np.fromfile(datafile, dtype=meta['dtype'][0])
    else:
        data = np.fromfile(datafile, dtype=np.float32)
    data = data.reshape(data.size // meta['vector_length'], meta['vector_length'])
    meta['utc_datetime'] = get_utc_datetime(np.mean(meta['times']))
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


def read_run(directory=None, update_v1=False, outpath=None):
    """Reads a CHART data run from the specified directory.
    
    Keyword arguments:
    directory -- the directory to read from (default: current directory)
    update_v1 -- if True, update metadata files from v1 to v2 format
                by asking the user for missing information (default: False)
    outpath -- if update_v1 is True, the directory to write updated 
                metadata files to (default: same as input directory, 
                overwriting existing files)
    """
    if directory is None:
        directory = os.curdir()
    data_list = find_dat_files(directory=directory)
    meta_list = find_meta_files(directory=directory)
    data = []
    meta = []
    # Check for old data format. Ask user for missing info. 
    # If not known, set to None
    metatemp = dict(np.load(meta_list[0], allow_pickle=True))
    if 'azimuth' not in metatemp:
        version = 1
        print(f'CHART v1 data format in {directory}.')
        print('Please enter the missing information (blank if unknown):')
        latitude = get_meta_param('Latitude [degrees]: ')
        longitude = get_meta_param('Longitude [degrees]: ')
        altitude = get_meta_param('Altitude [degrees]: ')
        azimuth = get_meta_param('Azimuth [degrees]: ')
        
        if update_v1:
            if outpath is None:
                outpath = directory
                print('Overwriting metadata files with new format...')
            else:
                print(f'Writing updated metadata files to {outpath}...')
    else: 
        version = 2
    for dfile, mfile in zip(data_list, meta_list):
        datatemp, metatemp = read_data(dfile, mfile)
        if version == 1:
            metatemp['azimuth'] = azimuth
            metatemp['altitude'] = altitude
            metatemp['latitude'] = latitude
            metatemp['longitude'] = longitude
            if update_v1:
                np.savez(mfile, **metatemp)
        data.append(datatemp)
        meta.append(metatemp)
    return data, meta



def concat(data_list):
    raise NotImplementedError()


def freq2vel(freq, rest=f_e):
    """
    Calculates velocity from measured frequency via doppler shift.
    
    :param freq: array of frequency quantities (including units)
    :param rest (optional): Rest frequency, defaults to 1.42 GHz
    :returns vel: velocity inferred by doppler shift
    """
    return (rest - freq) * speed_of_light / freq


def get_gal_coords(longitude, latitude, time, 
                   altitude, azimuth, return_vadj=False):
    """
    Determines galactic coordinates of an observation and
    optionally also calculates the velocity adjustment
    for the Local Standard of Rest.  
    
    :param latitude: latitude in degrees
    :param longitude: longitude in degrees
    :param time: observation time in UTC format string
    :param altitude: altitude in degrees
    :param azimuth: azimuth in degrees
    :param return_vadj (optional): If set to True, returns the 
                             velocity adjustment for the
                             Local Standard of Rest in addition
                             to the galactic coordinates (l, b).
                             If False (default) only returns (l, b).
    """
    
    loc = EarthLocation(lat=latitude*u.deg, lon=longitude*u.deg, height=0*u.m)
    altaz = AltAz(obstime=Time(time), location=loc, alt=altitude*u.deg, az=azimuth*u.deg)
    skycoord = SkyCoord(altaz.transform_to(ICRS()))
    if not return_vadj:
        return skycoord.galactic
    loc = loc.get_itrs(obstime=Time(time)) #To ITRS frame, makes Earth stationary with Sun 
    frequency = SpectralCoord(f_e, observer=loc, target=skycoord) #Shift expected from just local motion
    f_shifted = frequency.with_observer_stationary_relative_to('lsrk') #correct for kinematic local standard of rest
    f_shifted = f_shifted.to(u.GHz)
    v = -freq2vel(f_shifted, f_e)
    v_adj = v.to(u.km/u.second)
    return skycoord.galactic, v_adj

def find_array_with_number(arrs, number):
    """
    Find a number within a list of arrays. This is typically used to find
    the frequency tuning that contains a given frequency.

    :param arrs: List of arrays
    :param number: Number to find

    :returns: Index and array containing the number, or (None, None) if not found
    """
    for k_index, k in enumerate(arrs):
        if np.any((k[:-1] <= number) & (number <= k[1:])):
            return k_index, k
    return None, None

def average_overlapping(x1, y1, x2, y2, x3, y3):
    """
    Averages the y values where the x values are shared between 
    arrays and keeps y values for x values that are not shared.
    Assumes an x value is shared by at most two arrays.
    
    :param x1: First x array
    :param y1: First y array
    :param x2: Second x array
    :param y2: Second y array
    :param x3: Third x array
    :param y3: Third y array
    :return: Tuple of combined x values and averaged/kept y values
    """
    # Find the unique x values in both arrays
    unique_x = np.union1d(x1, x2)
    unique_x = np.union1d(unique_x, x3)
    
    # Create an array to store the averaged/kept y values
    avg_y = np.zeros(unique_x.shape)
    
    # Iterate over the unique x values
    for i in range(len(unique_x)):
        # Find the indices of the current x value in the two x arrays
        ind1 = np.where(x1 == unique_x[i])[0]
        ind2 = np.where(x2 == unique_x[i])[0]
        ind3 = np.where(x3 == unique_x[i])[0]
        
        # If the current x value is arrays 1 and 2
        if len(ind1) > 0 and len(ind2) > 0:
            # Compute the average of the two corresponding y values
            avg_y[i] = (y1[ind1[0]] + y2[ind2[0]]) / 2
        # If the current x value is only in the first array
        elif len(ind1) > 0:
            # Keep the corresponding y value from the first array
            avg_y[i] = y1[ind1[0]]
        # If the current x value is in arrays 2 and 3
        elif len(ind2) > 0 and len(ind3) > 0:
            # Compute the average of the two corresponding y values
            avg_y[i] = (y2[ind2[0]] + y3[ind3[0]]) / 2
        # If the current x value is only in the second array
        elif len(ind2) > 0:
            # Keep the corresponding y value from the second array
            avg_y[i] = y2[ind2[0]]
        # If the current x value is only in the third array
        elif len(ind3) > 0:
            # Keep the corresponding y value from the second array
            avg_y[i] = y3[ind3[0]]
    
    return unique_x, avg_y


def interactive_plot(x, max_amp=100, max_offset=100, max_width=15):
    """
    Creates a plot that can be modified with sliders.
    
    :param x: x values of overlapping CHART data
    :param max_amp (optional): Maximum amplitude for sliders. Default is 100.
    :param max_offset (optional): Maximum offset for sliders. Default is 100.
    :param max_width (optional): Maximum width for sliders. Default is 15.
    """
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    amp_default = 0
    offset_default = 0
    width_default = 5
    amps = [amp_default] * 4
    offsets = [offset_default] * 4
    widths = [width_default] * 4

    lines = [ax.plot(x, (amps[i]*(np.exp(-(((x-offsets[i])**2) / (2*(widths[i]**2)))))))[0] for i in range(4)]
    lines.append(ax.plot(x, sum([amps[i]*(np.exp(-(((x-offsets[i])**2) / (2*(widths[i]**2))))) for i in range(4)]))[0])

    amp_sliders = [FloatSlider(min=0, max=max_amp, step=0.1, value=amp_default, description=f'Amp {i+1}') for i in range(4)]
    offset_sliders = [FloatSlider(min=-100, max=max_offset, step=0.1, value=offset_default, description=f'Offset {i+1}') for i in range(4)]
    width_sliders = [FloatSlider(min=0, max=max_width, step=0.1, value=width_default, description=f'Width {i+1}') for i in range(4)]
    colors = ['black']*4 + ['red']
    color_dropdowns = [Dropdown(options=['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black'], value=colors[i], description=f'Color {i+1}') for i in range(4)]
    # display(HBox(color_dropdowns))
    
    ui = VBox([HBox(color_dropdowns), HBox(amp_sliders), HBox(offset_sliders), HBox(width_sliders)])
    color_dropdowns += [Dropdown(options=['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black'], value=colors[4], description=f'Sum color')]
    display(color_dropdowns[-1])
    def update(amp1=amp_default, offset1=offset_default, width1=width_default,
               amp2=amp_default, offset2=offset_default, width2=width_default,
               amp3=amp_default, offset3=offset_default, width3=width_default,
               amp4=amp_default, offset4=offset_default, width4=width_default):
        a = [amp1,amp2,amp3,amp4];
        b = [offset1,offset2,offset3,offset4]
        c = [width1,width2,width3,width4]
        for i in range(4):
            lines[i].set_ydata((a[i]*(np.exp(-(((x-b[i])**2) / (2*(c[i]**2)))))))
        lines[4].set_ydata(sum([a[i]*(np.exp(-(((x-b[i])**2) / (2*(c[i]**2))))) for i in range(4)]))
        for i in range(5):
            lines[i].set_color(color_dropdowns[i].value)
        fig.canvas.draw_idle()

    out = widgets.interactive_output(update, {'amp1':amp_sliders[0], 'offset1':offset_sliders[0], 'width1':width_sliders[0],
            'amp2':amp_sliders[1], 'offset2':offset_sliders[1], 'width2':width_sliders[1],
            'amp3':amp_sliders[2], 'offset3':offset_sliders[2], 'width3':width_sliders[2],
            'amp4':amp_sliders[3], 'offset4':offset_sliders[3], 'width4':width_sliders[3]})
    display(ui, out)
    
    return ax, offset_sliders

