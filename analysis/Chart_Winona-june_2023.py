#!/usr/bin/env python
# coding: utf-8

# # Analysis of CHART Data

# After you have both the metadata, which is the list of frequencies in each tuning for each pointing, and the observed data, which is the signal strength in decibels (dB) for each tuning for each pointing, you will have to analyze it in order to get to the final destination, an approximate rotation curve of the Milky Way galaxy. A rotation curve is a plot that shows how the orbital velocity of objects in a galaxy changes with their distance from the center of the galaxy. In other words, it shows how fast different parts of a galaxy are rotating around its center. Rotation curves are essential tools for studying the structure and dynamics of galaxies, as well as for understanding the distribution of mass within galaxies. By analyzing the shape of a galaxy’s rotation curve, scientists can learn about the distribution of visible and dark matter within the galaxy. Each point on the plot below refers to a hydrogen cloud within the Milky Way. 

# ![Rotation_curve_of_spiral_galaxy_Messier_33_%28Triangulum%29.png](attachment:Rotation_curve_of_spiral_galaxy_Messier_33_%28Triangulum%29.png)
# Image link: https://en.wikipedia.org/wiki/Galaxy_rotation_curve

# In each direction you pointed the telescope, you were looking at a specific line of sight within our galaxy.  

# ![Screenshot%202023-08-06%20221816.jpg](attachment:Screenshot%202023-08-06%20221816.jpg)

# ![Screenshot%202023-08-06%20223021.jpg](attachment:Screenshot%202023-08-06%20223021.jpg)

# The images above show the telescope's line of sight and field of view from two perspectives, one looking at the galaxy from a top-down view, and the other showing the area of the sky observed from Earth's surface. The FOV is the extent of the observable area measured in degrees that the telescope can see. Within the direction that the telescope is pointed towards, there are multiple neutral hydrogen clouds. If you look at the line of sight figure, you can see that the arrows cross through multiple parts of the galaxy. Gas from these areas will be moving at different velocities and directions. The positions of these hydrogen clouds can be defined by 2 metrics, the velocity of the cloud and its distance from the center. If you reference the rotation curve figure, you will see that those two parameters are what we use to reconstruct a rotation curve. This is what the analysis code below will find.  

# There are a few ways to identify positions in space. One is the celestial coordinate system. Right Ascension (RA) and Declination (Dec) are a system of coordinates used in astronomy to determine the location of stars, planets, and other objects in the night sky. They are similar to the system of longitude and latitude used to locate places on Earth. Right Ascension corresponds to longitude and Declination to latitude. 
# 
# ![RA-Dec-wiki-Tom-RuenCC-BY-SA-3.0.jpg](attachment:RA-Dec-wiki-Tom-RuenCC-BY-SA-3.0.jpg)
# Image link: https://skyandtelescope.org/astronomy-resources/right-ascension-declination-celestial-coordinates/

# Another is the galactic coordinate system. Galactic coordinates are a system of coordinates used in astronomy to determine the location of objects in the Milky Way galaxy. The system uses the Sun as its center, with the primary direction aligned with the approximate center of the Milky Way galaxy.
# 
# There are two coordinates in this system: galactic longitude (l) and galactic latitude (b). Galactic longitude is measured with the primary direction from the Sun to the center of the galaxy in the galactic plane, while galactic latitude measures the angle of the object above the galactic plane. 
# 
# ![GalLongLat_ofStar.jpg](attachment:GalLongLat_ofStar.jpg)
# Image link:https://astronomy.ua.edu/undergraduate-program/course-resources-astronomy/lab-exercise-8-cosmic-distributions-and-the-galactic-ecology/1293-2/

# Before we start the analysis it is important to review how the data was collected. 

# ![Screenshot%202023-07-21%20143438.jpg](attachment:Screenshot%202023-07-21%20143438.jpg)

# After the data is collected from the antenna it passes through a bandpass filter. A bandpass filter is used to isolate a specific frequency range of interest from the broader spectrum of electromagnetic radiation received by the telescope. This filter allows signals within the desired bandpass to pass through with little interference while blocking signals outside that range. After this process is complete the data moves to the Low Noise Amplifier. A Low Noise Amplifier is used to boost the weak radio frequency signals received by the antenna before further processing and analysis. Next, the data goes to the mixer. A mixer is a non-linear device that combines two or more signals to produce new signals at different frequencies.  Mixers generate a new frequency called the IF by combining the received signal with another signal called the local oscillator (LO). This lower frequency makes it easier to process and analyze the signals. Then an anti-aliasing filter is used to prevent aliasing artifacts when digitizing analog signals. Aliasing is the misidentification of a signal frequency which occurs when a signal is not adequately sampled, leading to distortion and false representation of the original signal. This filter prevents this from happening before data is digitized. In the image below, the teapot before anti-aliasing has misidentified the edges of the object, making it appear more ridged than it actually is. Through the anti-aliasing process, these errors are corrected. 
# 
# ![anti-aliasing-_antial1.fit_lim.size_1050x.gif](attachment:anti-aliasing-_antial1.fit_lim.size_1050x.gif)
# Image Link:https://www.pcmag.com/encyclopedia/term/anti-aliasing

# Run the cell below to import the packages.

# In[29]:


get_ipython().run_line_magic('matplotlib', 'inline')
import numpy
import numpy as np
import matplotlib.pyplot as plt
import chart
from astropy import units as u
from astropy.coordinates import SpectralCoord, EarthLocation, SkyCoord, AltAz, ICRS
from astropy.time import Time
import pandas as pd
import math
import scipy.stats
import scipy.stats as stats
from scipy.optimize import curve_fit
import ipywidgets as widgets
from ipywidgets import *
from ipywidgets import interact, FloatSlider, Dropdown
from scipy.stats import chi2


# # Data Preprocessing

# Run the cell below to input a few constanst and functions.

# In[30]:


# A couple constants and useful functions for later.
f0 = 1.420405751768  # GHz
speed_of_light = 299792458  # m/s
c = 3e8 * (u.meter/u.second)

def plot_f0(lims=[30, 40], xval=f0):
    plt.plot([xval, xval], lims, '--k', lw=0.5)
def f2v(freq):
    return -(np.array(freq)-f0) * speed_of_light / np.array(freq)
def doppler(shifted,rest):
    v = (c*(shifted-rest*u.GHz)/(shifted))
    return v 


# Input the file directory and the file names into the two lines below. Each file represents a single pointing. Input the file directory and the folder names into the two lines below and run the next three cells. Each folder represents a single pointing. A pointing is an observation made in a specific direction that can be defined by its altitude and azimuth, its celestial coordinates, or its galactic coordinates.   

# In[31]:


data_dir = '/data/'
paths = ['abeardsley_Winona-HS-Park_2022.10.08_1_6:12_pm','abeardsley_Winona-HS-Park_2022.10.8_2_6:25_pm',
         'abeardsley_Winona-HS-Park_2022.10.8_3_6:30_pm']

ntrials = len(paths)

data = []
mdata = []
bps = []  # bandpasses

for i in range(ntrials):
    d, m = chart.analysis.read_run(directory=data_dir + paths[i])
    d = np.array(d)
    data.append(d)
    mdata.append(m)
    # Rough estimate for bandpass
    nchans = m[0]['vector_length']
    levels = np.median(d[:, :, nchans // 4:(-nchans // 4)], axis=(1, 2))
    rescaled = d / levels.reshape(-1, 1, 1)
    bp = np.median(rescaled, axis=(0, 1))
    bps.append(bp)

chart.analysis.print_meta(m[0])


# In[32]:


ntrials = len(data)
spectra = [[] for _ in range(ntrials)]
freqs = [[] for _ in range(ntrials)]
nremove = nchans // 16


# In[33]:


for pointing in range(ntrials):
    for d, m in zip(data[pointing], mdata[pointing]):
        spectrum = np.mean(d, axis=0) 
        spectrum = 10*np.log10(spectrum)
        spectrum = spectrum[nremove:-nremove]
        frequencies = ((np.arange(m['vector_length']) - m['vector_length'] / 2)
                           * m['samp_rate'] / m['vector_length'] + m['frequency'])
        frequencies = 1e-9 * frequencies[nremove:-nremove]
        spectra[pointing].append(spectrum)
        freqs[pointing].append(frequencies)

    for k in range(len(spectra[pointing]) - 1):
        spec1 = spectra[pointing][k]
        spec2 = spectra[pointing][k + 1]
        freq1 = freqs[pointing][k]
        freq2 = freqs[pointing][k + 1]
        ncommon = np.sum([1 if f in freq2 else 0 for f in freq1])
        spec2 += np.median(spec1[-ncommon:]) - np.median(spec2[:ncommon])
        spectra[pointing][k + 1] = spec2


# The cell below plots the CHART data before the bandpass filter is applied. The x-axis represents the recorded frequencies(Ghz) and the y-axis shows the signal strength in decibels (dB) for each frequency. Each color represnts a different tunning and to make sure all frequencies are recorded accurately they over lap quite a bit. 

# In[34]:


plt.figure()
fig, axs = plt.subplots(ntrials, 1, sharex=True, figsize=(10,18))
for pointing in range(ntrials):
    for f, s in zip(freqs[pointing], spectra[pointing]):
        axs[pointing].plot(f, s)
    axs[pointing].set_title(f'Pointing {pointing+1}')
    axs[pointing].set_ylabel('[dB]')
    axs[pointing].axvline(1.4204)
#plt.xlim(1.42,1.421)   
plt.legend()
plt.xlabel('Frequency [GHz]')


# The next three cells plot the CHART data with the bandpass filter applied. 

# In[35]:


ntrials = len(data)
spectra = [[] for _ in range(ntrials)]
freqs = [[] for _ in range(ntrials)]
nremove = nchans // 16


# In[36]:


for pointing in range(ntrials):
    for d, m in zip(data[pointing], mdata[pointing]):
        spectrum = np.mean(d, axis=0) /bps[0]
        spectrum = 10*np.log10(spectrum)
        spectrum = spectrum[nremove:-nremove]
        frequencies = ((np.arange(m['vector_length']) - m['vector_length'] / 2)
                           * m['samp_rate'] / m['vector_length'] + m['frequency'])
        frequencies = 1e-9 * frequencies[nremove:-nremove]
        spectra[pointing].append(spectrum)
        freqs[pointing].append(frequencies)

    for k in range(len(spectra[pointing]) - 1):
        spec1 = spectra[pointing][k]
        spec2 = spectra[pointing][k + 1]
        freq1 = freqs[pointing][k]
        freq2 = freqs[pointing][k + 1]
        ncommon = np.sum([1 if f in freq2 else 0 for f in freq1])
        spec2 += np.median(spec1[-ncommon:]) - np.median(spec2[:ncommon])
        spectra[pointing][k + 1] = spec2


# In[37]:


plt.figure()
fig, axs = plt.subplots(ntrials, 1, sharex=True, figsize=(10,18))
for pointing in range(ntrials):
    for f, s in zip(freqs[pointing], spectra[pointing]):
        axs[pointing].plot(f, s)
    axs[pointing].set_title(f'Pointing {pointing+1}')
    axs[pointing].set_ylabel('[dB]')
    axs[pointing].axvline(1.4204)
#plt.xlim(1.42,1.421)   
plt.legend()
plt.xlabel('Frequency [GHz]')


# In[38]:


#Functions for code below
def LSR_shift(longitude, latitude, elevation, time, altitude, azimuth):
    """
    Identifies the exact postion at which the observations were taken and corrects for the Local Standard of Rest. 
    Along with this it also converts location, altitude, and azimuth to galactic coordinates.
    
    :param latitude: latitude in degrees
    :param longitude: longitude in degrees
    :param elevation: elevation in meters
    :param time: observation time in UTC format string
    :param altitude: altitude in degrees
    :param azimuth: azimuth in degrees
    """
    
    loc = EarthLocation(lat=latitude*u.deg, lon=longitude*u.deg, height=elevation*u.m)
    altaz = AltAz(obstime=Time(time), location=loc, alt=altitude*u.deg, az=azimuth*u.deg)
    skycoord = SkyCoord(altaz.transform_to(ICRS))
    location = EarthLocation.from_geodetic(longitude, latitude, elevation*u.m) #Lon, Lat, elevation
    location = location.get_itrs(obstime=Time(time)) #To ITRS frame, makes Earth stationary with Sun 
    pointing_45deg = SkyCoord(altaz.transform_to(ICRS)) #Center of CHART pointing
    frequency = SpectralCoord(1.420405751768e9 * u.Hz, observer=location, target=pointing_45deg) #Shift expected from just local motion
    f0_shifted = frequency.with_observer_stationary_relative_to('lsrk') #correct for kinematic local standard of rest
    f0_shifted = f0_shifted.to(u.GHz)
    v = doppler(f0_shifted,f0)
    v_adjustment = v.to(u.km/u.second)
    return v_adjustment, skycoord.galactic

def find_array_with_number(freqs, pointing, number):
    for k_index, k in enumerate(freqs[pointing]):
        if numpy.any((k[:-1] <= number) & (number <= k[1:])):
            return k_index, k
    return None, None

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

    #print("Chi-squared Statistic for x: ", chi_squared_statistic_x)
    #print("P-value for x: ", p_value_x)
    #print("Chi-squared Statistic for y: ", chi_squared_statistic_y)
    print("P-value for y: ", p_value_y)


# ## Comparison to Survey Data

# ## Pointing 1

# For each pointing, we will have to do a few corrections so that they are consistent with each other. The first of these corrections we will do is to correct the velocities of the hydrogen clouds to the Local Standard of Rest. The Local Standard of Rest (LSR) is a way for astronomers to measure the motion of objects in our galaxy, the Milky Way. Imagine you’re on a merry-go-round with your friends. The LSR is like the average speed and direction that everyone is moving. One is stationary with respect to this reference frame if they are moving at the same speed in the same direction. It helps establish a reference frame for understanding how stars and planets are moving in our galaxy. Along with this, we will need to convert your celestial coordinates to galactic coordinates. 
# 
# By inputting the exact location and UTC time that the observation along with the direction the antenna was pointed at we can correct the velocities r for Earth’s and the Sun’s constant movement. To get the UTC time, take the local time of your observations and adjust for your local time zone. 
# 
# Input information like this: (lon in degrees, lat in degrees, elevation in meters, dataTtime, Altitude in degrees, Azimuth in degrees)

# In[39]:


v_adjustment, galactic_coords =LSR_shift(-91.64419, 44.04672, 200, '2022-10-8T23:12:00', 90, 360)
print(v_adjustment)
print(galactic_coords)


# The printed out values are in galactic coordinates. 

# Once you have the galactic coordinates head to this website: https://www.astro.uni-bonn.de/hisurvey/euhou/LABprofile/index.php
# This database allows you to extract hydrogen profiles from the Leiden/Argentine/Bonn (LAB) Survey. The LAB Survey is a project that looked at the entire sky to study the gas in our Milky Way galaxy. They used two telescopes, one in the Netherlands and one in Argentina, to see the whole sky. They measured the light that is given off by hydrogen gas. By looking at this light, they could learn about where the gas is and how it moves. You can use this data to check your data and gain calibration to see if your observations were accurate or not.
# 
# Input the galactic coordinates and the beam size. The beam size of a telescope is the angular size of the area that the telescope can “see” at once. Imagine you’re looking through a paper towel roll. The width of the roll is like the beam size of the telescope, but instead of measuring it in inches or centimeters, we measure it in degrees. You can only see things that are within that angle. Since the simulator only allows beam size up to 20, set it to 20 degrees. It is important to note that the CHART beam size is actually closer to 25 degrees.

# Download the H1 profile file and upload it to Jupiter Notebook. 
# 
# ![Screenshot%202023-07-25%20160250.jpg](attachment:Screenshot%202023-07-25%20160250.jpg)
# 
# 

# ![Screenshot%202023-07-25%20160446%20%282%29.jpg](attachment:Screenshot%202023-07-25%20160446%20%282%29.jpg)

# To find the exact path to input below, go to your terminal and cd into the directory the file is located. Then use pwd which will print out the path. FInally, add an extra slash and the exact text file name.
# 
# ![Screenshot%202023-08-08%20141555.jpg](attachment:Screenshot%202023-08-08%20141555.jpg)

# In[40]:


sh_comp = pd.read_table('/data/HI_profiles_comparison/abeardsley_Winona-HS-Park_2022.10.08_1_6.12_pm.txt',skiprows=[0,1,2,3],names=['v_lsr', 'T_B', 'freq', 'wavel'], delimiter = '\s+')


# Have you ever noticed that the sound that comes from a car that is coming towards you sounds different than the sound that comes from the same car as it is moving away from you? That is because the sound waves are being condensed and stretched depending on the car’s position relative to your own. This is an example of the Doppler Effect. 

# ![Doppler Shift Example](https://flypaper.soundfly.com/wp-content/uploads/2018/01/doppler-effect-header.jpg)

# Image Link: https://flypaper.soundfly.com/wp-content/uploads/2018/01/doppler-effect-header.jpg
# 
# The same thing occurs with radio waves as objects in the universe move closer and farther away from us. The hydrogen clouds that the telescope detected are moving constantly and in order to find their velocity we have to use the Doppler shift equation. 

# ![Doppler Shift Equation](https://physicsopenlab.org/wp-content/uploads/2020/09/dopplerFormula2.png)

# This is the Doppler shift equation where fe is the rest frequency or the frequency of the hydrogen in a lab when it is not moving, fo is the wavelength we observe, c is the speed of light, and v is the velocity in km/s. By using this equation we can get accurate velocities of the hydrogen clouds in relation to us. The cell below does this calculation. 

# In[41]:


pointing = 0
velocity = f2v(freqs[pointing][k]*u.GHz) / 1000


# The variable (pointing) corresponds to each pointing that was defined above. Make sure the code is reading the pointing you want. For example, if you want to use pointing 1, you will put pointing = 0.

# In[42]:


number = 1.4204

k_index, result = find_array_with_number(freqs, pointing, number)
compTB = sh_comp['T_B']


# Next let us input the correction for the LSR into our equation. v_adjustment is the number you got from inputting the coordinates of  of the observation in the cell above.

# In[43]:


x = velocity*(u.kilometer)/(u.second)-v_adjustment


# Finally we have to do the calibration for both noise and gain. Noise calibration is the process of measuring and removing the effects of unwanted signals, or “noise,” from a measurement. Gain calibration is the process of measuring and adjusting the gain, or amplification, of a device to ensure that it is accurate. You can do both of these by adjusting the noise and running the cell. You are looking for the CHART data line to match up well with the Model line. 

# Along with this, make sure you name the plot acording to the pointing. You can do this by modifying the second to last line of code and inputting  your galactic coordinates. 

# In[44]:


noise = 3485
gain = max(10**(spectra[pointing][k_index+1]/10)-noise)/(max(compTB))

for k in range(len(freqs[pointing])):
    if k==k_index:
        (x,  (10**(spectra[pointing][k_index]/10)- noise)/gain)
    if k==k_index+1:
        (x,  (10**(spectra[pointing][k_index]/10) - noise)/gain)

x1 = np.array((f2v(freqs[pointing][k_index]*u.GHz) / 1000)*(u.kilometer)/(u.second)-v_adjustment)
y1 = np.array((10**(spectra[pointing][k_index]/10) - noise)/gain)
x2 = np.array((f2v(freqs[pointing][k_index+1]*u.GHz) / 1000)*(u.kilometer)/(u.second)-v_adjustment)
y2 = np.array((10**(spectra[pointing][k_index+1]/10) - noise)/gain)
unique_x, avg_y = average_overlapping(x1, y1, x2, y2)

get_ipython().run_line_magic('matplotlib', 'notebook')
ax=interactive_plot(unique_x)

ax.plot(unique_x, avg_y, 'tab:green', linewidth=2, label = 'CHART')
ax.plot(sh_comp['v_lsr'],compTB,'tab:orange', linewidth=2, label = 'Model')
plt.axvline(0, color ='k')
plt.xlim(-100,100)
ax.set_ylabel('[TB]')
ax.legend(loc='best')
plt.xlabel('Radial Velocity km/s')
plt.title('CHART HI Profile and Model Profile for l=71.5 and b=24.7 degrees')
plt.show


# Now, most likely when taking your data you captured multiple hydrogen clouds. This is because your antenna was looking in a direction and not at a point, along with the fact that there are many hydrogen clouds throughout the Milky Way. This means that there is a good chance there are multiple hydrogen clouds at different distances from you in that direction. We are looking for the highest velocity clouds to be able to use a method called the Tangent Point Method. This method makes certain assumptions about the way our galaxy rotates. One of the difficulties in measuring a rotation curve is that it is difficult to assign a specific velocity to a specific distance when observing multiple clouds along a line of sight. 
# 
# ![tangentSpeed.png](attachment:tangentSpeed.png)
# 
# Image link:https://physicsopenlab.org/2020/09/08/measurement-of-the-milky-way-rotation/

# One of the assumptions made by the TPM is that the angular speed of objects in the galaxy decreases with radius (distance from the center), so your smallest radius along that line of sight will always be the tangent point. We can use this assumption to assign a velocity to a specific location in the galaxy, as the highest velocity cloud will always correspond to a distance at the tangent point. In order to find the highest velocity cloud you will have to fit the data with the combined product of multiple Gaussian curves. For simplicity, you should only need up to four Gaussian curves to simulate the data since it is unlikely that the antenna picked up more than four distinct clouds. It is important to remember that you might not need four. If this is the case, leave the variables for the curves that you are not using at 0. Gaussian curves are often used to model the shape of spectral lines, such as those produced by hydrogen clouds. By fitting the data with multiple Gaussian curves, each curve can represent the signal from an individual hydrogen cloud. This allows you to separate the signal from each cloud and analyze them individually.
# 
# The sliders correspond to 4 different Gaussian curves whose combined product is the fifth curve. There are only 4 curves since it is unlikely that your observations detected more than 4 hydrogen clouds. You can change the colors to your liking. The “a” variable corresponds to the height of the curve, the “b” variable corresponds to its location on the x-axis. And the “c” variable corresponds to the width of the curve. You can change the size of the plot by dragging the bottom left corner.

# Once you have your combined curve input your values below and run the cell to test how well it lines up with the data

# In[17]:


# Gaussian curve 1
a1 = 2                        # height of the curve's peak
b1 = -75                        # the position of the center of the peak
c1 = 19                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y1 = (a1*(e ** -(((x-b1)**2) / (2*(c1**2)))))

# Gaussian curve 2
a2 = 1                        # height of the curve's peak
b2 = -32                        # the position of the center of the peak
c2 = 15                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y2 = (a2*(e ** -(((x-b2)**2) / (2*(c2**2)))))

# Gaussian curve 3
a3 = 9                        # height of the curve's peak
b3 = 4                        # the position of the center of the peak
c3 = 12                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y3 = (a3*(e ** -(((x-b3)**2) / (2*(c3**2)))))

# Gaussian curve 4
a4 = 0                        # height of the curve's peak
b4 = 0                        # the position of the center of the peak
c4 = 1                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y4 = (a4*(e ** -(((x-b4)**2) / (2*(c4**2)))))

combined_gauss = y1 + y2 + y3 + y4


# Run the next cell to perform a chi-squared goodness of fit test. A chi-squared goodness of fit test is a statistical test that compares the observed distribution of a categorical variable to an expected distribution. The test calculates a test statistic, which measures how far the observed values are from the expected values. If the test statistic is large, it means that the observed values are far from the expected values, and we can conclude that the observed distribution is significantly different from the expected distribution. The p-value is a number that helps us decide whether the observed distribution is different from the expected distribution. If the p-value is small, it means that the observed distribution is significantly different from the expected distribution. If the p-value is large, it means that we cannot say for sure whether the observed distribution is different from the expected distribution. If your p-value is above 0.05 your combined curve lines up well. If not, adjust your numbers and repeat the process. 

# In[18]:


goodness_of_fit(unique_x, combined_gauss, avg_y)


# In[19]:


import numpy as np
from scipy.stats import chi2

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

print("Reduced Chi-squared Statistic for xy: ", reduced_chi_squared_statistic_xy)
print("P-value for xy: ", p_value_xy)


# ## Pointing  2

# In[20]:


v_adjustment, galactic_coords = LSR_shift(-91.64419, 44.04672, 200, '2022-10-8T23:25:00', 53, 180)
print(v_adjustment)
print(galactic_coords)


# In[21]:


sh_comp = pd.read_table('/data/HI_profiles_comparison/abeardsley_Winona-HS-Park_2022.10.8_2_6.25_pm.txt',skiprows=[0,1,2,3],names=['v_lsr', 'T_B', 'freq', 'wavel'], delimiter = '\s+')


# In[22]:


pointing = 1
velocity = f2v(freqs[pointing][k]*u.GHz) / 1000


# In[ ]:


number = 1.4204

k_index, result = find_array_with_number(freqs, pointing, number)

compTB = sh_comp['T_B']


# In[ ]:


x = velocity*(u.kilometer)/(u.second)-v_adjustment


# In[ ]:


noise = 2315
gain = max(10**(spectra[pointing][k_index+1]/10)-noise)/(max(compTB))

for k in range(len(freqs[pointing])):
    if k==k_index:
        (x,  (10**(spectra[pointing][k_index]/10)- noise)/gain)
    if k==k_index+1:
        (x,  (10**(spectra[pointing][k_index]/10) - noise)/gain)

x1 = np.array((f2v(freqs[pointing][k_index]*u.GHz) / 1000)*(u.kilometer)/(u.second)-v_adjustment)
y1 = np.array((10**(spectra[pointing][k_index]/10) - noise)/gain)
x2 = np.array((f2v(freqs[pointing][k_index+1]*u.GHz) / 1000)*(u.kilometer)/(u.second)-v_adjustment)
y2 = np.array((10**(spectra[pointing][k_index+1]/10) - noise)/gain)
unique_x, avg_y = average_overlapping(x1, y1, x2, y2)

get_ipython().run_line_magic('matplotlib', 'notebook')
ax=interactive_plot(unique_x)

ax.plot(unique_x, avg_y, 'tab:green', linewidth=2, label = 'CHART')
ax.plot(sh_comp['v_lsr'],compTB,'tab:orange', linewidth=2, label = 'Model')
plt.axvline(0, color ='k')
plt.xlim(-100,100)
ax.set_ylabel('[TB]')
ax.legend(loc='best')
plt.xlabel('Radial Velocity km/s')
plt.title('CHART HI Profile and Model Profile for l=36.5 and b=8.5 degrees')
plt.show


# In[ ]:


# Gaussian curve 1
a1 = 7                        # height of the curve's peak
b1 = -4                        # the position of the center of the peak
c1 = 43                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y1 = (a1*(e ** -(((x-b1)**2) / (2*(c1**2)))))

# Gaussian curve 2
a2 = 33                        # height of the curve's peak
b2 = 4                        # the position of the center of the peak
c2 = 6                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y2 = (a2*(e ** -(((x-b2)**2) / (2*(c2**2)))))

# Gaussian curve 3
a3 = 15                        # height of the curve's peak
b3 = 22                        # the position of the center of the peak
c3 = 9                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y3 = (a3*(e ** -(((x-b3)**2) / (2*(c3**2)))))

# Gaussian curve 4
a4 = 5                        # height of the curve's peak
b4 = 57                        # the position of the center of the peak
c4 = 19                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y4 = (a4*(e ** -(((x-b4)**2) / (2*(c4**2)))))

combined_gauss = y1 + y2 + y3 + y4


# In[ ]:


goodness_of_fit(unique_x, combined_gauss, avg_y)


# In[ ]:


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

print("Reduced Chi-squared Statistic for xy: ", reduced_chi_squared_statistic_xy)
print("P-value for xy: ", p_value_xy)


# ## Pointing  3

# In[ ]:


v_adjustment, galactic_coords = LSR_shift(-91.64419, 44.04672, 200, '2022-10-08T23:30:00', 17, 180)
print(v_adjustment)
print(galactic_coords)


# In[ ]:


sh_comp = pd.read_table('/data/HI_profiles_comparison/abeardsley_Winona-HS-Park_2022.10.8_3_6.30_pm.txt',skiprows=[0,1,2,3],names=['v_lsr', 'T_B', 'freq', 'wavel'], delimiter = '\s+')


# In[ ]:


pointing = 2
velocity = f2v(freqs[pointing][k]*u.GHz) / 1000


# In[ ]:


number = 1.4204

k_index, result = find_array_with_number(freqs, pointing, number)

compTB = sh_comp['T_B']


# In[ ]:


x = velocity*(u.kilometer)/(u.second)-v_adjustment


# In[ ]:


noise = 3160
gain = max(10**(spectra[pointing][k_index+1]/10)-noise)/(max(compTB))

for k in range(len(freqs[pointing])):
    if k==k_index:
        (x,  (10**(spectra[pointing][k_index]/10)- noise)/gain)
    if k==k_index+1:
        (x,  (10**(spectra[pointing][k_index]/10) - noise)/gain)

x1 = np.array((f2v(freqs[pointing][k_index]*u.GHz) / 1000)*(u.kilometer)/(u.second)-v_adjustment)
y1 = np.array((10**(spectra[pointing][k_index]/10) - noise)/gain)
x2 = np.array((f2v(freqs[pointing][k_index+1]*u.GHz) / 1000)*(u.kilometer)/(u.second)-v_adjustment)
y2 = np.array((10**(spectra[pointing][k_index+1]/10) - noise)/gain)
unique_x, avg_y = average_overlapping(x1, y1, x2, y2)

get_ipython().run_line_magic('matplotlib', 'notebook')
ax=interactive_plot(unique_x)

ax.plot(unique_x, avg_y, 'tab:green', linewidth=2, label = 'CHART')
ax.plot(sh_comp['v_lsr'],compTB,'tab:orange', linewidth=2, label = 'Model')
plt.axvline(0, color ='k')
plt.xlim(-100,100)
ax.set_ylabel('[TB]')
ax.legend(loc='best')
plt.xlabel('Radial Velocity km/s')
plt.title('CHART HI Profile and Model Profile for l=4.9 and b=-9 degrees')
plt.show


# In[ ]:


# Gaussian curve 1
a1 = 10                        # height of the curve's peak
b1 = -9                        # the position of the center of the peak
c1 = 14                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y1 = (a1*(e ** -(((x-b1)**2) / (2*(c1**2)))))

# Gaussian curve 2
a2 = 19                        # height of the curve's peak
b2 = 0                        # the position of the center of the peak
c2 = 4                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y2 = (a2*(e ** -(((x-b2)**2) / (2*(c2**2)))))

# Gaussian curve 3
a3 = 24                        # height of the curve's peak
b3 = 8                        # the position of the center of the peak
c3 = 3                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y3 = (a3*(e ** -(((x-b3)**2) / (2*(c3**2)))))

# Gaussian curve 4
a4 = 14                        # height of the curve's peak
b4 = 12                        # the position of the center of the peak
c4 = 18                        # the standard deviation
e = 2.71828                  # Euler's number
x = unique_x
y4 = (a4*(e ** -(((x-b4)**2) / (2*(c4**2)))))

combined_gauss = y1 + y2 + y3 + y4


# In[ ]:


goodness_of_fit(unique_x, combined_gauss, avg_y)


# In[ ]:


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

print("Reduced Chi-squared Statistic for xy: ", reduced_chi_squared_statistic_xy)
print("P-value for xy: ", p_value_xy)


# Now that you have separated the individual clouds in the data it is time to identify the highest-velocity cloud. If your data is in the first quadrant (l=0-90), then you are looking for the x-value for the highest velocity curve, (its b-value). If your data is in the fourth quadrant (l=270-360), then you are looking for the x-value for the lowest velocity curve. The reason for this disparity has to do with the direction the clouds are moving. Clouds in the first quadrant are moving away from us and are therefore redshifted. When using the Doppler equation these clouds will give us positive values. On the other hand, clouds in the fourth quadrant are moving toward us and are therefore blueshifted.  When using the Doppler equation these clouds will give us negative values. The number you will use is the absolute value of the velocity you get from this process. 

# In[ ]:





# With the highest velocity cloud of each of your pointings, we will use the Tangent Point Method to find their true velocity and distance from the center of the galaxy. This method involves looking at the motion of gas clouds in the Milky Way and using their observed velocities to calculate how fast different parts of the galaxy are rotating. By doing this for many different points in the galaxy, we can create a graph that shows the rotation curve of the Milky Way.

# Take the curve with the highest velocity (the one farthest to the right) and take its velocity (the b value) along with the galactic longitude the observation was made and input them into the arrays below.

# In[26]:


Vobs = np.array([4,57,12])                #observed velocity
long = np.array([78.8,48.9,14.1])                #galactic longitude

Vsun = 220             #estimated velocity of the sun
Ro = 7.6               #estimated distance of the sun to the center of the galaxy in kiloparsecs

V_observed = Vobs + Vsun*np.sin(np.deg2rad(long)) #Calculates the tangent speed of the cloud with respect to the galactic center
d_observed = Ro*np.sin(np.deg2rad(long))                      #Calculates the distance of the cloud from the center of the Milky Way

V_expected = [137, 156, 198, 208, 214, 227, 213, 221, 232, 233, 236, 213, 229, 229, 229, 229, 231, 233, 235, 240, 242, 242, 240]
d_expected = [2.76, 3.15, 3.53, 3.91, 4.62, 4.96, 5.28, 5.59, 5.88, 6.17, 6.43, 6.67, 6.90, 7.10, 7.29, 7.46, 7.61, 7.74, 7.84, 7.92, 7.99, 8.03, 8.04]


# In[27]:


get_ipython().run_line_magic('matplotlib', 'notebook')
plt.scatter(d_observed, V_observed, color='tab:blue', linewidth=2, label = 'Observed Data')
plt.scatter(d_expected, V_expected, color='tab:red', linewidth=2, label = 'Expected Data')
plt.legend(loc='best')
plt.xlabel('Distance from Galactic Center (kpc)')
plt.ylabel('Rotation Velocity (km/s)')
plt.title('Rotation Curve')
plt.show()


# In[ ]:




