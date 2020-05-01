
Welcome to the CHART project
======
## Chart stands for "Completly Hackable Amateur Radio Telescope."</br>
Our online tutorials will guide you step-by-step in creating your own radio telescope at home or in the classroom.

---
We recommend that the users builds the telescope first through the tutorials in the hardware section, then navigate to the software section where we will be taking data from the sky.

You can visit the website at this link:
https://astrochart.github.io

---

To get started, here is a list of materials you will need for software installation:
- Raspberry Pi 3B
-Micro SD Card (32GB)
- RTL-SDR
- A computer monitor
- Ethernet cable (if not using WiFi option)
- Radio antenna
- Personal computer
- Keyboard
- Horn/Antenna

---

Before starting this tutorial, it’s highly recommended to go through the ‘Software Vocabulary’ section to get familiar with the concepts explained in the following tutorial.

Most of us are familiar with using a Mac or PC computer and are comfortable with this kind of set up. This project’s set up is going to be different than these systems, but not difficult to navigate after spending some time getting familiar with all of the components. For this project, we will be using a Raspberry Pi as our computing device. This type of computing device doesn’t store data locally, so we will need to use an SD card for storage. Since we will be starting with a computing device that doesn’t have a preinstalled OS or GUI, we will need to set these up so that we can interact with the computer with ease. We chose Ubuntu (a version of Linux) as our OS along with the MATE GUI extension.
To get started, we need to make sure that all our wires are hooked up and ready to go.  
- Hook up your Raspberry Pi to your monitor.
- Plug in your ethernet cable (or wifi).
- Plug in your Raspberry Pi into a power source.
- Hook up to your keyboard (we used a wireless hook up for ours).

For the following steps of installing Ubuntu MATE I followed the tutorial below presented by Tech Radar.
https://www.techradar.com/how-to/how-to-install-ubuntu-on-the-raspberry-pi

<h2>Download Ubuntu MATE</h2>
For the following steps of installing Ubuntu MATE I followed the tutorial below
https://www.techradar.com/how-to/how-to-install-ubuntu-on-the-raspberry-pi
 First, we will need to install Ubuntu Mate as our operating system and GUI. You can skip the ‘Installing Ubuntu Mate' section of this tutorial if you choose to purchase an SD card with Ubuntu MATE pre-installed.

 If you choose to install yourself, we will need our personal computer in order to do the first step in this process.

 To download Ubuntu MATE we will use our personal computer and visit https://ubuntu-mate.org/download/ and click on “Raspberry Pi (Recommended)”. At the time of writing this, I chose “10.04.2 Bionic” as the release version that I am running.

 ---

<h2>Decompressing the file</h2>
After downloading this, we will need to install a decompression utility in order to read the Ubuntu file.
For Mac: The Unarchiver is available free from the App Store to extract the .xz file. Once the utility is installed, double-click the file in your downloads to extract the image (.img) file.
For Windows:  Go to the 7-Zip website to install the application. Click on ‘Download’, choose ‘Save’. Go to ‘Downloads’ in File Explorer. Double click on the ‘7-Zip’ file. Choose ‘Install’.
I’m using a Mac, and my steps/downloads looked like this:
Here I have ‘The Unarchiver’ decompression utility downloading that I downloaded from the app store.
I saved both of these downloads next to each other on my desktop for easy navigation.

After opening my Ubuntu file by double clicking, my file converted and saved on my desktop.

---
<h2>Formatting the Micro SD card</h2>
For the micro SD card to be compatible with the  Raspberry Pi, it has to be formatted to FAT32.  
For Mac: In order for your microSD card to be compatible with the Raspberry Pi it must be formatted to FAT32.
Connect the microSD card to your mac. The system will automatically mount it. Click ‘Spotlight’ at the top right of the screen, type ‘Disk Utility’ and press return.
Once Disk Utility launches, select the microSD card from the list of available disks in the pane on the left. Click the ‘Erase’ tab, then select ‘MS-DOS (FAT)’ from the ‘Format’ drop down menu.
You can also set a name for the microSD card here e.g. MY SD 1. Click the ‘Erase’ button when you’re ready.
For Windows: Insert your SD card into the slot on your computer or a USB adapter.
Windows will now inform you that you need to format the disk in order to continue. Click ‘Format Disk’. Next, you can choose the format, file system, allocation unit size and volume label. Windows will warn you that formatting will erase all previous data on the SD card. Choose ‘Ok’ to continue. The device will then be formatted.
If you don’t see the above notification, open Windows Explorer. Search for the SD drive. Right-click on this and from the drop-down menu, select format. Windows will automatically default to FAT32.

 ---

<h2>Download and Install Etcher </h2>
This allows us to write our file onto our micro SD card. You can download Etcher here https://www.balena.io/etcher/ .
Once you open Etcher it will prompt you to select an image. Select Ubuntu MATE, and then click ‘Flash’. This process might take up to 20 mins.
If you would like to do this step through command line in your terminal, you can visit step 7 in the linked tutorial at the beginning of this tutorial.

 ---

<h2>Set Up Ubuntu MATE on Raspberry Pi</h2>
After the writing process is done, safely eject your micro SD card and place it into your Raspberry Pi.

Where to place SD card in Raspberry Pi
Make sure all connections we set up in the beginning of the tutorial are still in place so that our system will start up on the monitor screen.
The system will now prompt you to choose your location settings, and to set up your computer system names. Once this set up process is complete, the Ubuntu MATE desktop will open.
The OS will display a welcome message and offer you a tour of Ubuntu’s features. Make sure to go through this if you haven’t used the MATE desktop environment before.

 ---

<h2>Updates </h2>
The version of Ubuntu MATE you have now installed may not be fully up-to-date.
To check if this is the case, go to System > Software Updater.
The system will now scan for updates. A box will appear stating ‘Updated software has been issued since Ubuntu x.04 was released. Do you wish to update?’. Click ‘Install Now’ to update your system.
Troubleshooting
Some Ubuntu MATE users have reported issues with connecting to Wi-Fi after install, the network manager says the ‘device not ready’. This issue is specific to the Raspberry Pi 3. fortunately restarting the Raspberry Pi almost always fixes this problem.
Other users have reported issues installing and upgrading software using the built-in software updater. If this happens, open the MATE Terminal. Next, run the command:
sudo apt-get update
then:
sudo apt-get upgrade
That should fix the issue and you'll now have Ubuntu MATE running on your Raspberry Pi!
You have now successfully installed Ubuntu MATE onto your Raspberry Pi!

 ---

<h2>Install GNU Radio</h2>
GNU Radio is the free open source software that we will be using to help us process our data. To learn more about GNU Radio visit this site https://www.gnuradio.org/about/ .
Make sure that you have an internet connection for these next steps. We used an ethernet hook up to ensure that we had an internet connection, but you can also hook up to wifi if available.
Plug in the RTL-SDR device into the Raspberry Pi.
To install gnuradio on Ubuntu, open up your terminal (found under the menu tab on the top left -> system tools -> MATE Terminal)  and type in the following command:
    sudo apt install gnuradio-dev gr-osmosdr librtlsdr-dev build-essential git cmake ipython
Press enter.
You will be prompted for your password, provide password and press enter.
It will ask you to continue after using a certain amount of disk space.
Type  y and press enter.
This download might take up to 20 mins.
 Next, open up your newly installed gnuradio by typing in this command in the terminal:
    gnuradio-companion
