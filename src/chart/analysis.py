import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import time
from astropy import units as u
from astropy.coordinates import SpectralCoord, EarthLocation, SkyCoord, AltAz, ICRS
from astropy.time import Time
from ipywidgets import interact, FloatSlider, Dropdown, HBox, VBox, widgets
import scipy.constants as const
from scipy.ndimage import median_filter

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


def interactive_plot(unique_x):
    """
    Creates a plot that can be modified with sliders.
    
    param unique_x: x values of overlapping CHART data
    """
    x = unique_x
    e = 2.71828  
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    a = b = c = [1]*4

    lines = [ax.plot(x, (a[i]*(e ** -(((x-b[i])**2) / (2*(c[i]**2))))))[0] for i in range(4)]
    lines.append(ax.plot(x, sum([a[i]*(e ** -(((x-b[i])**2) / (2*(c[i]**2)))) for i in range(4)]))[0])

    sliders = [FloatSlider(min=-100, max=100, step=1, value=1) for _ in range(12)]
    colors = ['black']*4 + ['red']
    color_dropdowns = [Dropdown(options=['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black'], value=colors[i]) for i in range(5)]

    def update(a1=1, b1=1, c1=1, a2=1, b2=1, c2=1, a3=1, b3=1, c3=1, a4=1, b4=1, c4=1,
               color1='black', color2='black', color3='black', color4='black', color5='red'):
        a = [a1,a2,a3,a4]
        b = [b1,b2,b3,b4]
        c = [c1,c2,c3,c4]
        for i in range(4):
            lines[i].set_ydata((a[i]*(e ** -(((x-b[i])**2) / (2*(c[i]**2))))))
        lines[4].set_ydata(sum([a[i]*(e ** -(((x-b[i])**2) / (2*(c[i]**2)))) for i in range(4)]))
        for i in range(5):
            lines[i].set_color([color1,color2,color3,color4,color5][i])
        fig.canvas.draw_idle()

    interact(update,
             a1=sliders[0], b1=sliders[1], c1=sliders[2],
             a2=sliders[3], b2=sliders[4], c2=sliders[5],
             a3=sliders[6], b3=sliders[7], c3=sliders[8],
             a4=sliders[9], b4=sliders[10], c4=sliders[11],
             color1=color_dropdowns[0], color2=color_dropdowns[1],
             color3=color_dropdowns[2], color4=color_dropdowns[3],
             color5=color_dropdowns[4])
     
    return ax

    
def goodness_of_fit(unique_x, combined_gauss, avg_y):
    """Performs a chi-squared goodness of fit test between the CHART data and the user created combined Gaussian curve.
    
    param unique_x: x values of overlapping CHART data
    param combined_gauss: y values of combined Gaissian curve
    param avg: y values of overlapping CHART data
    """
    x_observed = np.array(unique_x)
    y_observed = np.array(combined_gauss)
    x_expected = np.array(unique_x) * 2
    y_expected = np.array(avg_y) * 2

    observed = np.concatenate((x_observed.reshape(-1,1), y_observed.reshape(-1,1)), axis=1)
    expected = np.concatenate((x_expected.reshape(-1,1), y_expected.reshape(-1,1)), axis=1)

    mask = (observed[:,0] >= -100) & (observed[:,0] <= 100)
    observed_masked = observed[mask]
    expected_masked = expected[mask]

    chi_squared_statistic_x = np.sum((observed_masked[:,0] - expected_masked[:,0])**2 / expected_masked[:,0])
    chi_squared_statistic_y = np.sum((y_observed - y_expected)**2 / y_expected)

    p_value_x = chi2.sf(chi_squared_statistic_x, len(observed_masked[:,0]) - 1)
    p_value_y = chi2.sf(chi_squared_statistic_y, len(y_observed) - 1)

    chi_squared_statistic_xy = chi_squared_statistic_x + chi_squared_statistic_y
    degrees_of_freedom_xy = len(observed) - 2
    reduced_chi_squared_statistic_xy = chi_squared_statistic_xy / degrees_of_freedom_xy
    p_value_xy = chi2.sf(reduced_chi_squared_statistic_xy, degrees_of_freedom_xy)
    return reduced_chi_squared_statistic_xy, p_value_xy
