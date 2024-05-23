
# CHART
## The Completly Hackable Amateur Radio Telescope
https://astrochart.github.io

We created this project to make astronomy accessible to anyone that is interested and bring opportunities to learn about radio astronomy to a broad audience. You can find our full mission statement on our [About page](https://astrochart.github.io/website/about.html).

Our online tutorials will guide you step-by-step in creating your own radio telescope at home or in the classroom.

The tutorials are a work in progress, but so far will walk you through:
- Acquiring materials and equipment
- Setting up a Raspberry Pi to run GNU Radio
- Taking data with GNU Radio and a Software Define Radio (SDR)
- Building a feed horn to detect the 21cm signal from the Milky Way galaxy

---

### Software Installation

Here we provide the software installation instructions to get you started.

*Note the 2023 release of Raspberry Pi OS (Bookworm) does not allow global pip installs. You will need to set up a virtual environment:*
```bash
python -m venv --system-site-packages ~/chartenv
source chartenv/bin/activate
```

#### Analysis Only
<details>
<summary>Click for analysis only instructions</summary>

If you are only using the analysis code, you can simply clone the repo and use pip to install. This is the install using ssh. 
```bash
git clone git@github.com:astrochart/CHART.git
cd CHART
pip install .
```
If you want to use https, use this:
```bash
git clone https://github.com/astrochart/CHART.git
cd CHART
pip install .
```
</details>

#### Full Install
<details>
<summary>Click for full installation instructions</summary>

CHART software uses GNU Radio, a free open source package for collecting and processing radio data.
To learn more about GNU Radio visit this site https://www.gnuradio.org/about/.

We will assume you are running Raspberry Pi OS on a Raspberry Pi (instructions  [here](https://astrochart.github.io/website/software.html)).
First make sure you have activated your virtual environment (see above).

In a terminal, enter the following:
```bash
sudo apt install gnuradio-dev gr-osmosdr librtlsdr-dev build-essential git cmake xterm
```

If you are using the RTL-SDR Blog v4 dongle, we need to update the driver. Full details are [here](https://www.rtl-sdr.com/v4/),
and we have included the relevant commands below for convenience.
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

A few useful python libraries:
```bash
pip install ipython numpy juypter
```

To use the GPS submodule (optional), run these lines:
```bash
sudo apt install gpsd gpsd-clients
pip install gps
```

Clone this repository and install. 
```bash
git clone https://github.com/astrochart/CHART.git
cd CHART
pip install .
```
</details>

---
