## Building the 21cm CHART disk image

**This page is meant for developers planning to make changes to code.**
If you are looking for the default Raspberry PI setup, use the [latest pre-built sd card image](https://astrochart.github.io/telescope_design#burn-your-micro-sd-card).

What follows is the procedure for building the CHART disk image.
The latest version is `v2.0` (see changelog below).

The basic procedure is to install all the necessary software on Raspberry PI and then clone the disk. We have found that
sometimes details matter in the setup, so the below is a log of everything we've done for the most recent build. These
instructions work as of the most recent entry in the changelog below. 


## Setup the PI
- We used the official [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to put Raspberry Pi OS (64-bit) on a
micro SD card.
The target device was Raspberry Pi 4.
We used a 16 GB card because we found 8 GB to be a tad too small.
- Next we booted up the Pi with the new SD card. We set the time zone to US Central, US Keyboard, and we used the generic username and password `pi` and `raspberry`, respectively. We skipped setting up wifi. We selected to use Chromium and uninstalled firefox. We did not enable Raspberry Pi Connect. We did the overall software update.
- In Preferences > Control Centre > System, we disabled Admin Password
- In Preferences > Control Centre > Screens, we changed the display resolution to `800x600`
- In File Manager > Edit > Preferences > General, we enabled "Don't ask options on launch executable file"
- When opening up the web browser a blank keyring was chosen by clicking continue
- Once everything was updated and rebooted, we opened a terminal and set up a virtual python environment:
```bash
python -m venv --system-site-packages ~/chartenv
source chartenv/bin/activate
```
- We appended the second line above to the `~.bashrc` file so the `chartenv` environment will always activate when a terminal is opened.
- Next we installed `gnuradio` and other packages.
```bash
sudo apt install build-essential git cmake xterm gnuradio-dev librtlsdr0 librtlsdr-dev rtl-sdr gr-osmosdr stellarium
```
- Next, we blacklisted the default DVB kernel driver so the RTL-SDR can be accessed by user-space software and prevent Bias-T issues with the Blog v4. See [their user guide](https://www.rtl-sdr.com/V4/) for details.
```bash
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee --append /etc/modprobe.d/blacklist-dvb_usb_rtl28xxu.conf
```
The BNO085 seems to work best on the Raspberry Pi with an I2C clock frequency of 400kHz. You can make that change by adding this line to your /boot/firmware/config.txt file.
```
dtparam=i2c_arm_baudrate=400000
```
- We rebooted the system.
- Finally we installed CHART.
```bash
git clone https://github.com/astrochart/CHART.git
cd CHART
pip install .
```
- In `/home/pi/chartenv/bin/chart-observe.py`, we added the following line to the `buildWindow()` function to launch the GUI in full-screen mode:
```python
self.attributes("-zoomed", True)
``` 
>[!NOTE]
>This modification is applied only to the disk image because the `"-zoomed"` window attribute is Linux specific and would not work on other operating systems. 

At this point everything was installed and the Pi was ready to be used. 


## Clone the disk to an IMG
The following steps are used to create the actual `.img.xz` file for backup and sharing.

- Unnecessary files, Trash and the .cache folder were removed from the pi to free up space. The following command was used to clean up space from the install above: 
```bash
sudo apt clean
```

**On a separate linux computer:**

- With the sd inserted we found the device using `lsblk`
- We then made a raw image using `dd` via the following command where `/dev/sdb` is the sd device: 
```bash 
sudo dd if=/dev/sdb of=chart.img bs=4M status=progress
```
> [!CAUTION]
> `dd` performs a raw disk copy and can permanently overwrite data. Verify the source (`if=`) and destination (`of=`) devices before pressing Enter. An incorrect destination may destroy the contents of a drive.
- Then we shrunk the image using PiShrink
```bash
wget https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh
chmod +x pishrink.sh
sudo ./pishrink.sh chart.img
```
- To further shrink the image size, we compressed the `chart.img` with `xz` 
```bash
xz -T0 -9 chart.img
```


## CHART Disk Image Change Log

#### v2.0.2 (8 July, 2026)
- [View detailed changes to CHART](https://github.com/astrochart/CHART/compare/v2.0..v2.0.2)
- Changed disk image driver install
  - Fixed a hanging issue when running a default scan 
  - Install now uses default Debian packages for librtlsdr and rtl-sdr for Blog v4
  - Install only requires blacklist for DVB-T drivers 

#### v2.0 (29 June, 2026)
- [View detailed changes to CHART](https://github.com/astrochart/CHART/compare/v1.1..v2.0)
- Complete GUI overhaul
  - Added logging and removed the need for terminal
  - Changed date and time to be handled by the system
  - Added a plot feature when data collection is finished
  - Added location calculation and the ability to save settings
  - New pointing calculator and observation planner
- Streamlined data collection
  - Updated the command line tool 
  - Updated file names 
  - All user information is now saved through metadata
- Improved Installation
  - Added a script that creates a launcher when installed
  - Added a .toml file due to deprecation of setup.py
- Updated analysis tutorial
  - Calibration improvement based on Memo 13
  - Improvements to interactive fitting
  - Added simple median filter option

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
