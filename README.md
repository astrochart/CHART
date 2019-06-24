
Welcome to the CHART project 
======
## Chart stands for "Completly Hackable Amateur Radio Telescope".</br>
Our online tutorials will guide you step-by-step in creating your own radio telescope at home or in the classroom. 

---
To get started, here is a list of materials you will need for software instillation:</br>
- Raspberry Pi 3B</br>
- RTL-SDR</br>
- A computer moniter </br>
-Ethernet cable (if not using WiFi option)
-Radio antenna


---

First you will want to download Ubuntu MATE. Here is a link to their website.
https://ubuntu-mate.org/download/ 
Click on "Raspberry Pi (Reccommended)
Then click on the release that you would like; we chose 18.04.2 (Bionic) which is supported until April 2021. 
Save this somewhere that is easily accessible. 

Now that we have our OS system/interface, we can set up our GNU radio and start taking data. 

---
## Setting up GNU Radio
(If you would like to see screen shots of this process, visit our 'software' tab on the CHART website.)</br>
1. Plug the Raspberry Pi into your monitor. Plug in the RTL-SDR device into the Raspberry Pi. 
To install gnuradio on Ubuntu, open up your terminal and type in the following command:
   " sudo apt install gnuradio-dev gr-osmosdr librtlsdr-dev build-essential git cmake ipython "

2. Next, open up your newly installed gnuradio by typing in this command in the terminal:
   " gnuradio-companion "

3. After gnuradio opens, make a simple flow chart by locating the RTL-SDR Source block and QT GUI Sink block and connecting them together. I also modified my Variable box to a Value: 1M, but this is only a personal preference. 

4. Connect radio antenna source to the RTL-SDR input so that we can see real radio data in our program. Make sure to elongate the antennas fully so that you can receive a strong radio signal. 

5. Click the “Generate the flow graph” button, to transform our flow chart into python code. Next click the “Execute the flow graph button” to create a real time data plot of the incoming radio signals. 

6. A new window will pop up that displays incoming radio data. You can click on the tabs at the top of the screen to view the data in “Frequency”, “Waterfall”, “Time Domain”, or “Constellation” display. 
Congratulations, you have collected your first radio data set!





