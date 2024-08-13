## Building the 21cm CHART disk image

**This page is meant for developers planning to make changes to code.**
If you are looking for the default Raspberry PI setup, use the [latest pre-built sd card image](https://astrochart.github.io/telescope_design#burn-your-micro-sd-card).

What follows is the procedure for building the CHART disk image.
The latest version is `v1.1` (see changelog below).

The basic procedure is to install all the necessary software on Raspberry PI and then clone the disk. We have found that
sometimes details matter in the setup, so the below is a log of everything we've done for the most recent build. These
instructions work as of the most recent entry in the changelog below. 


## Setup the PI
- We used the official [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to put Raspberry Pi OS (64-bit) on a
micro SD card.
The target device was Raspberry Pi 4.
We used a 16 GB card because we found 8 GB to be a tad too small.
- Next we booted up the Pi with the new SD card. We set the time zone to US Central, US Keyboard, and we used the generic username and password `pi` and `raspberry`, respectively. We skipped setting up wifi. We selected to use Chromium and uninstalled firefox. We did not enable Raspberry Pi Connect. We did the overall software update.
- Once everything was updated and rebooted,   we opened a terminal and set up a virtual python environment:
```bash
python -m venv --system-site-packages ~/chartenv
source chartenv/bin/activate
```
- We appended the second line above to the `~.bashrc` file so the `chartenv` environment will always activate when a terminal is opened.
- Next we installed `gnuradio` and other packages.
```bash
sudo apt install gnuradio-dev gr-osmosdr librtlsdr-dev build-essential git cmake xterm
```
- The next chunk of commands were needed to install the latest RTL-SDR blog driver for v4 support. See [their user guide](https://www.rtl-sdr.com/V4/) for details.
```bash
sudo apt install libusb-1.0-0-dev
sudo apt install debhelper
git clone https://github.com/rtlsdrblog/rtl-sdr-blog
cd rtl-sdr-blog
sudo dpkg-buildpackage -b --no-sign
cd ..
sudo dpkg -i librtlsdr0_*.deb
sudo dpkg -i librtlsdr-dev_*.deb
sudo dpkg -i rtl-sdr_*.deb
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee --append /etc/modprobe.d/blacklist-dvb_usb_rtl28xxu.conf
```
- We rebooted the system.
- Finally we installed CHART.
```bash
git clone https://github.com/astrochart/CHART.git
cd CHART
pip install .
```
- We used `vi` to make a bash script called chart-observe on the Desktop with the following lines:
```bash
#!/bin/bash
source /home/pi/chartenv/bin/activate
chart-observe.py
```
- We made the script executable:
```bash
chmod 777 ~/Desktop/chart-observe
```

At this point everything was installed and the Pi was ready to be used. 


## Clone the disk to an ISO
The following steps are used to create the actual `.iso` file for backup and sharing.

- We used Mac's Disk Utility app to create an image, using format "DVD/CD Master" with no encryption.
- When the image was complete, we changed the extension from "cdr" to "iso."
- We then copied the file to a linux system and used [pishrink](https://github.com/Drewsif/PiShrink) to shrink it.
```bash
wget https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh
chmod +x pishrink.sh
sudo ./pishrink.sh chart.iso
```

## CHART Disk Image Change Log

#### v1.1 (30 July, 2024)
- [View detailed changes to CHART](https://github.com/astrochart/CHART/compare/v1.0..v1.1)
- Streamlined install process.
- Fixes to analysis tutorial, added test data.
- GUI changes
  - renamed to `chart-observe.py`
  - Updated default parameters
  - Made Bias-T warning more clear
  - No longer save filenames with colons (which break in Windows)

#### v1.0 (23 May, 2024)
- Initial image creation.
- CHART git hash [61f6c7](https://github.com/astrochart/CHART/tree/61f6c7a69daa4efa9d26ac73410de8999d55b2ac)
