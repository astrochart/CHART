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
    return data_list


def find_meta_files(directory=None):
    if directory is None:
        directory = os.curdir()
    meta_list = sorted(glob.glob(os.path.join(directory, '*.npz')))
    return meta_list


def read_run(directory=None):
    data_list = find_dat_files(directory=directory)
    meta_list = find_meta_files(directory=directory)
    data = []
    meta = []
    for dfile, mfile in zip(data_list, meta_list):
        datatemp, metatemp = read_data(dfile, mfile)
        data.append(datatemp)
        meta.append(metatemp)
    return data, meta


def concat(data_list):
    raise NotImplementedError()


def LSR_shift(lon, lat, ele, time, RA, Dec):
    """
    Identifies the exact postion at which the observations were taken and corrects for the Local Standard of Rest.
    
    :param lon: longitude 
    :param lat: latitude
    :param ele: elevation
    :param time: date and time
    :param RA: Right Ascension
    :param Dec: Declination
    """
    
    location = EarthLocation.from_geodetic(lon, lat, ele*u.m) #Lon, Lat, elevation
    location = location.get_itrs(obstime=Time(time)) #To ITRS frame, makes Earth stationary with Sun 
    pointing_45deg = SkyCoord(RA,Dec, frame='icrs') #Center of CHART pointing
    frequency = SpectralCoord(1.420405751768e9 * u.Hz, observer=location, target=pointing_45deg) #Shift expected from just local motion
    f0_shifted = frequency.with_observer_stationary_relative_to('lsrk') #correct for kinematic local standard of rest
    f0_shifted = f0_shifted.to(u.GHz)
    v = doppler(f0_shifted,f0)
    v_adjustment = v.to(u.km/u.second)
    print(v_adjustment)
    return v_adjustment


def average_overlapping(x1, y1, x2, y2):
    """
    Averages the y values where the x values are shared between two arrays and keeps y values for x values that are not shared.
    
    :param x1: First x array
    :param y1: First y array
    :param x2: Second x array
    :param y2: Second y array
    :return: Tuple of combined x values and averaged/kept y values
    """
    # Find the unique x values in both arrays
    unique_x = np.union1d(x1, x2)
    
    # Create an array to store the averaged/kept y values
    avg_y = np.zeros_like(unique_x)
    
    # Iterate over the unique x values
    for i in range(len(unique_x)):
        # Find the indices of the current x value in the two x arrays
        ind1 = np.where(x1 == unique_x[i])[0]
        ind2 = np.where(x2 == unique_x[i])[0]
        
        # If the current x value is in both arrays
        if len(ind1) > 0 and len(ind2) > 0:
            # Compute the average of the two corresponding y values
            avg_y[i] = (y1[ind1[0]] + y2[ind2[0]]) / 2
        # If the current x value is only in the first array
        elif len(ind1) > 0:
            # Keep the corresponding y value from the first array
            avg_y[i] = y1[ind1[0]]
        # If the current x value is only in the second array
        elif len(ind2) > 0:
            # Keep the corresponding y value from the second array
            avg_y[i] = y2[ind2[0]]
    
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
    a1 = a2 = a3 = a4 = b1 = b2 = b3 = b4 = c1 = c2 = c3 = c4 = 1

    line1, = ax.plot(x, (a1*(e ** -(((x-b1)**2) / (2*(c1**2))))))
    line2, = ax.plot(x, (a2*(e ** -(((x-b2)**2) / (2*(c2**2))))))
    line3, = ax.plot(x, (a3*(e ** -(((x-b3)**2) / (2*(c3**2))))))
    line4, = ax.plot(x, (a4*(e ** -(((x-b4)**2) / (2*(c4**2))))))
    line5, = ax.plot(x, ((a1*(e ** -(((x-b1)**2) / (2*(c1**2))))) + 
                         (a2*(e ** -(((x-b2)**2) / (2*(c2**2))))) + 
                         (a3*(e ** -(((x-b3)**2) / (2*(c3**2))))) + 
                         (a4*(e ** -(((x-b4)**2) / (2*(c4**2)))))))

    a1_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    a2_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    a3_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    a4_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    b1_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    b2_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    b3_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    b4_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    c1_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    c2_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    c3_slider = FloatSlider(min=-100, max=100, step=1, value=1)
    c4_slider = FloatSlider(min=-100, max=100, step=1, value=1)

    color1_dropdown = Dropdown(options=['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black'], value='black')
    color2_dropdown = Dropdown(options=['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black'], value='black')
    color3_dropdown = Dropdown(options=['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black'], value='black')
    color4_dropdown = Dropdown(options=['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black'], value='black')
    color5_dropdown = Dropdown(options=['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black'], value='red')

    def update(a1=1, b1=1, c1=1, a2=1, b2=1, c2=1, a3=1, b3=1, c3=1, a4=1, b4=1, c4=1, 
               color1='black', color2='black', color3='black', color4='black', color5='red'):
        line1.set_ydata((a1*(e ** -(((x-b1)**2) / (2*(c1**2))))))
        line2.set_ydata((a2*(e ** -(((x-b2)**2) / (2*(c2**2))))))
        line3.set_ydata((a3*(e ** -(((x-b3)**2) / (2*(c3**2))))))
        line4.set_ydata((a4*(e ** -(((x-b4)**2) / (2*(c4**2))))))
        line5.set_ydata(((a1*(e ** -(((x-b1)**2) / (2*(c1**2))))) + 
                         (a2*(e ** -(((x-b2)**2) / (2*(c2**2))))) + 
                         (a3*(e ** -(((x-b3)**2) / (2*(c3**2))))) + 
                         (a4*(e ** -(((x-b4)**2) / (2*(c4**2)))))))
        line1.set_color(color1)
        line2.set_color(color2)
        line3.set_color(color3)
        line4.set_color(color4)
        line5.set_color(color5)
        fig.canvas.draw_idle()

    interact(update, a1=a1_slider, b1=b1_slider, c1=c1_slider, a2=a2_slider, b2=b2_slider, c2=c2_slider, 
             a3=a3_slider, b3=b3_slider, c3=c3_slider, a4=a4_slider, b4=b4_slider, c4=c4_slider, color1=color1_dropdown, 
             color2=color2_dropdown, color3=color3_dropdown, color4=color4_dropdown, color5=color5_dropdown);
     
    return ax


def goodness_of_fit(unique_x, combined_gauss, avg_y):
    """Performs a chi-squared goodness of fit test between the CHART data and the user created combined Gaussian curve.
    
    param unique_x: x values of overlapping CHART data
    param combined_gauss: y values of combined Gaissian curve
    param avg: y values of overlapping CHART data
    """
    x_gauss = np.array(unique_x)
    y_gauss = np.array(combined_gauss)
    x_data = np.array(unique_x) 
    y_data = np.array(avg_y) 

    gauss = np.concatenate((x_gauss.reshape(-1,1), y_gauss.reshape(-1,1)), axis=1)
    data = np.concatenate((x_data.reshape(-1,1), y_data.reshape(-1,1)), axis=1)


    mask = (gauss[:,0] >= -100) & (gauss[:,0] <= 100)
    gauss_masked = gauss[mask]
    data_masked = data[mask]

    chi_squared_statistic_x = np.sum((gauss_masked[:,0] - data_masked[:,0])**2 / data_masked[:,0])
    chi_squared_statistic_y = np.sum((y_gauss - y_data)**2 / y_data)

    p_value_x = chi2.sf(chi_squared_statistic_x, len(gauss_masked[:,0]) - 1)
    p_value_y = chi2.sf(chi_squared_statistic_y, len(y_gauss) - 1)

    print("P-value for y: ", p_value_y)
