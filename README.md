
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

CHART software uses GNU Radio, a free open source package for collecting and processing radio data.
To learn more about GNU Radio visit this site https://www.gnuradio.org/about/.

We will assume you are running Ubuntu MATE on a Raspberry Pi (instructions  [here](https://astrochart.github.io/website/software.html)).

In a terminal, enter the following:
```bash
sudo apt install gnuradio-dev gr-osmosdr librtlsdr-dev build-essential git cmake ipython
pip install numpy gps
```

To use the GPS submodule (optional), run these lines:
```bash
sudo apt install gpsd gpsd-clients
pip install gps
```

Clone this repository and install.
```bash
git clone git@github.com:astrochart/CHART.git
cd CHART
python setup.py install
```

---
