#!/usr/bin/python3
import tkinter
import customtkinter
import os
import subprocess
import datetime
import time
import glob
import shutil
import webbrowser
import re
import threading
import numpy as np
import chart
import sys
import matplotlib.pyplot as plt

from tkinter import messagebox
from argparse import Namespace
from freq_and_time_scan import buildConfig, runObservation
from chart.azalt import pointing, azalt, gps

class ChartApp(customtkinter.CTk):

    def __init__(self):
        super().__init__()

        self.session = None     # Data collection thread is stored here
        self.jupyter_proc = None    # jupyter local subprocess
        self.last_data_dir = None   # stores last directory created for plotting function

        #storage for stdout/stderr pipe required to capture GNU radio messages 
        self._log_pipe_r = None
        self._log_pipe_w = None
        self._stdout_saved = None
        self._stderr_saved = None

        self.default_freq_i = "1415"
        self.default_freq_f = "1425"
        self.default_int_time = "5"
        self.default_nint = "10"

        self.buildWindow()
        self.buildWidgets()

    def buildWindow(self):

        #builds main GUI window and captures when GUI is closed

        customtkinter.set_appearance_mode("light")
        customtkinter.set_default_color_theme("blue")

        self.geometry("786x480")
        self.title("CHART Data Collection")

        self.protocol(
            "WM_DELETE_WINDOW",
            self.onClose
        )
    
    def buildWidgets(self):  
        #set up GUI frames and widgets that are not inside the scroll frame

        # Top bar spanning the full width — its own 3-column grid keeps these
        # from piling into one cell, and isolates this layout from the body.
        self.top_bar = customtkinter.CTkFrame(self, fg_color="transparent")
        self.top_bar.grid(column=0, row=0, padx=5, pady=2, sticky="ew")
        self.top_bar.grid_columnconfigure(0, weight=1)   # left  (switch)
        self.top_bar.grid_columnconfigure(1, weight=1)   # center (buttons)
        self.top_bar.grid_columnconfigure(2, weight=1)   # right (clock)
        
        self.mode_switch = customtkinter.CTkSwitch(self.top_bar, text="Dark Mode", command=self.toggleDarkMode, onvalue="on", offvalue="off")
        self.mode_switch.grid(column=0, row=0, padx=10, pady=2, sticky="w")
        
        self.button_frame = customtkinter.CTkFrame(self.top_bar, fg_color="transparent")
        self.button_frame.grid(column=1, row=0, pady=2)   # centered in its column
        
        self.pointing_button = customtkinter.CTkButton(self.button_frame, text="Pointing Calculator", width=160, command=self.openPointingCalculator, hover_color = "purple")
        self.pointing_button.grid(column=0, row=0, padx=5)
        
        self.time_button = customtkinter.CTkButton(self.button_frame, text="Set System DateTime", width=160, command=self.openTimeWindow)
        self.time_button.grid(column=1, row=0, padx=5)
        
        self.clock_frame = customtkinter.CTkFrame(self.top_bar, fg_color="transparent")
        self.clock_frame.grid(column=2, row=0, padx=2, pady=2, sticky="e")
        self.clock_label_description = customtkinter.CTkLabel(self.clock_frame, text="Observation Time: ")
        self.clock_label_description.grid(column=0, row=0, padx=2, pady=2, sticky="e")
        self.clock_label = customtkinter.CTkLabel(self.clock_frame, text="")
        self.clock_label.grid(column=1, row=0, padx=2, pady=2, sticky="w")
        self.updateClock()

        # defines what rows can expand
        self.rowconfigure(0, weight=0)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(1, weight=1) 
        self.rowconfigure(0, weight=0)
        self.columnconfigure(0, weight=1)

        self.scroll_frame = customtkinter.CTkScrollableFrame(self)
        self.scroll_frame.grid(column=0, row=1, padx=10, pady=0, sticky="nsew")
        self.scroll_frame.columnconfigure(1, weight=1)
        self.scroll_frame.columnconfigure(3, weight=1)

        self.terminal = customtkinter.CTkTextbox(self, height=80)
        self.terminal.grid(row=2, column=0, sticky="ew", padx=10, pady=(0,10))
        self.terminal.configure(state="disabled")

        #widgets inside of the scroll frame is called with the following functions
        self.buildEntries()
        self.buildSwitches()
        self.buildButtons()
    
    def buildEntries(self):


        #left side
        self.observer_name_label = customtkinter.CTkLabel(self.scroll_frame, text="Observer Name")
        self.observer_name_label.grid(column=0, row=0, padx=10, pady=5)
        self.observer_name_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="Enter Here")
        self.observer_name_entry.grid(column=1, row=0, padx=10, pady=5, sticky="ew")

        self.location_label = customtkinter.CTkLabel(self.scroll_frame, text="Location")
        self.location_label.grid(column=0, row=1, padx=10, pady=5, sticky="n")
        self.location_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="Enter Here")
        self.location_entry.grid(column=1, row=1, padx=10, pady=5, sticky="nwe")

        self.latitude_label = customtkinter.CTkLabel(self.scroll_frame, text="Latitude")
        self.latitude_label.grid(column=0, row=3, padx=10, pady=5)
        self.latitude_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="Enter Here")
        self.latitude_entry.grid(column=1, row=3, padx=10, pady=5, sticky="ew")

        self.longitude_label = customtkinter.CTkLabel(self.scroll_frame, text="Longitude")
        self.longitude_label.grid(column=0, row=4, padx=10, pady=5, sticky="n")
        self.longitude_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="Enter Here")
        self.longitude_entry.grid(column=1, row=4, padx=10, pady=5, sticky="nwe")

        self.altitude_label = customtkinter.CTkLabel(self.scroll_frame, text="Altitude (deg)")
        self.altitude_label.grid(column=0, row=5, padx=10, pady=5)
        self.altitude_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="Enter Here")
        self.altitude_entry.grid(column=1, row=5, padx=10, pady=5, sticky="ew")

        self.azimuth_label = customtkinter.CTkLabel(self.scroll_frame, text="Azimuth (deg)")
        self.azimuth_label.grid(column=0, row=6, padx=10, pady=5, sticky="n")
        self.azimuth_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="Enter Here")
        self.azimuth_entry.grid(column=1, row=6, padx=10, pady=5, sticky="nwe")

        self.description_label = customtkinter.CTkLabel(self.scroll_frame, text="Description (optional)")
        self.description_label.grid(column=0, row=7, padx=10, pady=5, sticky="sew")
        self.description_entry = customtkinter.CTkTextbox(self.scroll_frame, height=50)
        self.description_entry.grid(column=0, row=8, padx=10, pady=5, sticky="news", columnspan=2, rowspan=2)


        #adding in a real time moniter of lat and long for the pointing calculator, this will auto input the lat and long from the main menu to the pointing calculator menu
        self.latitude_entry.bind("<KeyRelease>",  lambda e: self.syncCoords(self.latitude_entry,  "pointing_latitude_entry"))
        self.latitude_entry.bind("<FocusOut>",    lambda e: self.syncCoords(self.latitude_entry,  "pointing_latitude_entry"))
        self.longitude_entry.bind("<KeyRelease>", lambda e: self.syncCoords(self.longitude_entry, "pointing_longitude_entry"))
        self.longitude_entry.bind("<FocusOut>",   lambda e: self.syncCoords(self.longitude_entry, "pointing_longitude_entry"))
        #sync coords is defined above the open pointing calculator definition


        #right side
        self.frequency_label = customtkinter.CTkLabel(self.scroll_frame, text="Frequency Scan Setup")
        self.frequency_label.grid(column=2, row=0, padx=10, pady=5, sticky="we")

        self.frequency_start_label = customtkinter.CTkLabel(self.scroll_frame, text="Start Frequency (MHz)")
        self.frequency_start_label.grid(column=2, row=3, padx=10, pady=5)
        self.frequency_start_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="1415")
        self.frequency_start_entry.grid(column=3, row=3, padx=10, pady=5, sticky="ew")

        self.frequency_stop_label = customtkinter.CTkLabel(self.scroll_frame, text="Stop Frequency (MHz)")
        self.frequency_stop_label.grid(column=2, row=4, padx=10, pady=5, sticky="n")
        self.frequency_stop_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="1425")
        self.frequency_stop_entry.grid(column=3, row=4, padx=10, pady=5, sticky="nwe")

        self.integration_time_label = customtkinter.CTkLabel(self.scroll_frame, text="Integration time (s)")
        self.integration_time_label.grid(column=2, row=5, padx=10, pady=5, sticky="n")
        self.integration_time_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="5")
        self.integration_time_entry.grid(column=3, row=5, padx=10, pady=5, sticky="nwe")

        self.integration_scans_label = customtkinter.CTkLabel(self.scroll_frame, text="Integrations per scan step")
        self.integration_scans_label.grid(column=2, row=6, padx=10, pady=5, sticky="n")
        self.integration_scans_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="10")
        self.integration_scans_entry.grid(column=3, row=6, padx=10, pady=5, sticky="nwe")

    def buildSwitches(self):
        self.default_switch = customtkinter.CTkSwitch(self.scroll_frame, text="Use Defualt Parameters", onvalue="on", offvalue="off", command=self.enableDefaults)
        self.default_switch.grid(column=2, row=1, padx=10, pady=10, sticky="w")

        self.bias_switch = customtkinter.CTkSwitch(self.scroll_frame, text="Enable Bias-T", onvalue="on", offvalue="off", command=self.biasTwarn)
        self.bias_switch.grid(column=2, row=7, padx=10, pady=10, sticky="w")
    
    def buildButtons(self):
        self.start_button = customtkinter.CTkButton(self.scroll_frame, text="Start", command=self.startCollection)
        self.start_button.grid(column=2, row=8, padx=10, pady=3, sticky="ew")

        self.stop_button = customtkinter.CTkButton(self.scroll_frame, text="Stop", command=self.stopCollection)
        self.stop_button.grid(column=3, row=8, padx=10, pady=3, sticky="ew")

        self.jupyter_upload_button = customtkinter.CTkButton(self.scroll_frame, text="Upload to Jupyter Hub", command=self.jupyter_upload)
        self.jupyter_upload_button.grid(column=2, row=9, padx=10, pady=3, sticky="new")

        self.jupyter_local_button = customtkinter.CTkButton(self.scroll_frame, text="Local Jupyter Notebook", command=self.jupyter_local)
        self.jupyter_local_button.grid(column=3, row=9, padx=10, pady=3, sticky="new")
    
    def log(self, message):

        # adds log command to a loop to prevent application freezing as it waits for a log message

        self.after(0, self._log, message)

    def _log(self, message):

        # logs message to "terminal" text box

        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"{message}\n")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def submitTime(self):

        # a command that will verify time values and set system date and time

        try:
            day = int(self.day_menu.get())
            month = int(self.month_menu.get())
            year = int(self.year_menu.get())
            hour = int(self.hour_menu.get())
            minute = int(self.minute_menu.get())
        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "All fields must be integers.", parent=self.popup
            )
            return

        if not (1 <= day <= 31):
            messagebox.showerror("Error", "Day must be between 1 and 31.", parent=self.popup)
            return

        if not (1 <= month <= 12):
            messagebox.showerror("Error", "Month must be between 1 and 12.", parent=self.popup)
            return

        if not (2026 <= year <= 2080):
            messagebox.showerror("Error", "Year must be between 2026 and 2080.", parent=self.popup)
            return

        if not (0 <= hour <= 23):
            messagebox.showerror("Error", "Hour must be between 0 and 23.", parent=self.popup)
            return

        if not (0 <= minute <= 59):
            messagebox.showerror("Error", "Minute must be between 0 and 59.", parent=self.popup)
            return

        date_time = datetime.datetime(
            year,
            month,
            day,
            hour,
            minute
        )
        
        timeChange = subprocess.run(["sudo", "-n", "date", "-s", str(date_time)])
        
        if timeChange.returncode != 0:
            self.log("ERROR: Could not set system date and time. Administrator permisions are required")
        else:
            self.log(f"{date_time} is set!")
            self.updateClock()

    def openTimeWindow(self):

        # a simple popup menu that will set system date and time using spinboxes and submittime() function

        self.popup = customtkinter.CTkToplevel(self)
        self.popup.title("System Date and Time")
        self.popup.geometry("240x200")
        self.popup.columnconfigure(1, weight=1) #defines what columns can expand
        self.popup.columnconfigure(0, weight=1)


        self.day_var = tkinter.StringVar(value="1")
        self.month_var = tkinter.StringVar(value="1")
        self.year_var = tkinter.StringVar(value="2026")
        self.hour_var = tkinter.StringVar(value="12")
        self.minute_var = tkinter.StringVar(value="00")

        self.day_menu_label = customtkinter.CTkLabel(self.popup, text="Day:")
        self.day_menu_label.grid(column=0, row=1, sticky="e", padx=10)
        self.day_menu = tkinter.Spinbox(self.popup, from_=1, to=31, textvariable=self.day_var, width=5)
        self.day_menu.grid(column=1, row=1)

        self.month_menu_label = customtkinter.CTkLabel(self.popup, text="Month:")
        self.month_menu_label.grid(column=0, row=2, sticky="e", padx=10)
        self.month_menu = tkinter.Spinbox(self.popup, from_=1, to=12, textvariable=self.month_var, width=5)
        self.month_menu.grid(column=1, row=2)

        self.year_menu_label = customtkinter.CTkLabel(self.popup, text="Year:")
        self.year_menu_label.grid(column=0, row=3, sticky="e", padx=10)
        self.year_menu = tkinter.Spinbox(self.popup, from_=2026, to=2080, textvariable=self.year_var, width=5)
        self.year_menu.grid(column=1, row=3)

        self.day_menu_label = customtkinter.CTkLabel(self.popup, text="Hour (0-24)")
        self.day_menu_label.grid(column=0, row=4, sticky="e", padx=10)
        self.hour_menu = tkinter.Spinbox(self.popup, from_=0, to=23, textvariable=self.hour_var, width=5)
        self.hour_menu.grid(column=1, row=4)

        self.day_menu_label = customtkinter.CTkLabel(self.popup, text="Minute")
        self.day_menu_label.grid(column=0, row=5, sticky="e", padx=10)
        self.minute_menu = tkinter.Spinbox(self.popup, from_=0, to=59, textvariable=self.minute_var, width=5,)
        self.minute_menu.grid(column=1, row=5)

        self.submit_button = customtkinter.CTkButton(self.popup, text="Set System Time", command=self.submitTime)
        self.submit_button.grid(column=0, row=6, sticky="s", columnspan=2)

        self.popup.wait_visibility() # prevents the GUI trying to access the popup before it is fully created. 
        self.popup.focus() # brings popup in front of GUI
        self.popup.grab_set() # freezes main GUI

    #function to connect lat long in the main menu to lat long in the pointing window in real time
    def syncCoords(self, source, target, event=None):
        if isinstance(target, str):
            target = getattr(self, target, None)
        if target is not None and target.winfo_exists():
            target.delete(0, "end")
            target.insert(0, source.get())
   
    def openPointingCalculator(self):
    
        self.window = customtkinter.CTkToplevel(self)
        self.window.title("Pointing Calculator")
        self.window.geometry("500x500")
    
        self.scroll = customtkinter.CTkScrollableFrame(master = self.window, width = 460, height = 260)
        self.scroll.pack(fill = "both", expand = True, padx = 10, pady = 10)
    
        # === Row 0-1: Lat-Long ===#
        #Will automatically pull the lat and long from the main window if theyre filled in

        existing_lat = self.latitude_entry.get()

        self.latitude_label = customtkinter.CTkLabel(self.scroll, text = "Latitude:", justify = "left")
        self.latitude_label.grid(row = 0, column = 0, sticky = "w", padx = 10, pady = 5)
        self.pointing_latitude_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "e.g.: 40.7128", width = 180)
        self.pointing_latitude_entry.grid(row = 1, column = 0, sticky = "w", padx = 10, pady = 5)
        if existing_lat:                                            # only if non-blank
            self.pointing_latitude_entry.insert(0, existing_lat)


        existing_long = self.longitude_entry.get()

        self.longitude_label = customtkinter.CTkLabel(self.scroll, text = "Longitude:", justify = "left")
        self.longitude_label.grid(row = 0, column = 1, sticky = "w", padx = 10, pady = 5)
        self.pointing_longitude_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "e.g.: -74.0060", width = 180)
        self.pointing_longitude_entry.grid(row = 1, column = 1, sticky = "w", padx = 10, pady = 5)
        if existing_long:                                            # only if non-blank
            self.pointing_longitude_entry.insert(0, existing_long)

        self.pointing_latitude_entry.bind("<KeyRelease>",  lambda e: self.syncCoords(self.pointing_latitude_entry, self.latitude_entry))
        self.pointing_latitude_entry.bind("<FocusOut>",    lambda e: self.syncCoords(self.pointing_latitude_entry, self.latitude_entry))

        
        self.pointing_longitude_entry.bind("<KeyRelease>", lambda e: self.syncCoords(self.pointing_longitude_entry, self.longitude_entry))
        self.pointing_longitude_entry.bind("<FocusOut>",   lambda e: self.syncCoords(self.pointing_longitude_entry, self.longitude_entry))

        # === Row 2-3 increments ===#
        self.latitude_increment_label = customtkinter.CTkLabel(
            self.scroll, text="Galactic Latitude Spacing (b)\n(Degrees between points):", justify = "left")
        self.latitude_increment_label.grid(row = 2, column = 0, sticky = "w", padx = 10, pady = 5)
        self.latitude_increment_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "e.g.: 10", width = 180)
        self.latitude_increment_entry.grid(row = 3, column = 0, sticky = "w", padx = 10, pady = 5)
    
        self.longitude_increment_label = customtkinter.CTkLabel(
            self.scroll, text="Galactic Longitude Spacing (l)\n(Degrees between points):", justify = "left")
        self.longitude_increment_label.grid(row = 2, column = 1, sticky = "w", padx = 10, pady = 5)
        self.longitude_increment_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "e.g.: 10", width = 180)
        self.longitude_increment_entry.grid(row = 3, column = 1, sticky = "w", padx = 10, pady = 5)
    
        # === Row 4-5 Num_points and Delay ===#
        self.num_points_label = customtkinter.CTkLabel(self.scroll, text = "Number of Data Points:", justify = "left")
        self.num_points_label.grid(row = 4, column = 0, sticky = "w", padx = 10, pady = 5)
        self.num_points_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "e.g.: 5", width = 180)
        self.num_points_entry.grid(row = 5, column = 0, sticky = "w", padx = 10, pady = 5)
    
        self.delay_label = customtkinter.CTkLabel(self.scroll, text = "Minutes until first point:", justify = "left")
        self.delay_label.grid(row = 4, column = 1, sticky = "w", padx = 10, pady = 5)
        self.delay_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "e.g.: 2 for 2 minutes", width = 180)
        self.delay_entry.grid(row = 5, column = 1, sticky = "w", padx = 10, pady = 5)
    
        # === Row 6: Calculate button (this was missing entirely) ===#
        self.calculate_button = customtkinter.CTkButton(self.scroll, text="Calculate", command=self.calculate, width = 180, hover_color = "dark blue")
        self.calculate_button.grid(row = 6, column = 0, padx = 10, pady = 5)

        self.advanced_button = customtkinter.CTkButton(self.scroll, text="Advanced Pointing", command=self.advancedPointing, width = 180, fg_color = "purple", hover_color = "red")
        self.advanced_button.grid(row = 6, column = 1,  padx = 10, pady = 5)
    
        # === Box where the AzAlt text goes ===#
        self.AzAlt_box = customtkinter.CTkTextbox(self.scroll, width=440, height=200, state = "disabled")
        self.AzAlt_box.grid(row = 7, column = 0, columnspan = 2, sticky = "w", padx = 10, pady = 5)

    def advancedPointing(self):
        self.window = customtkinter.CTkToplevel(self)
        self.window.title("Advanced Pointing")
        self.window.geometry("500x500")
    
        self.scroll = customtkinter.CTkScrollableFrame(master = self.window, width = 460, height = 260)
        self.scroll.pack(fill = "both", expand = True, padx = 10, pady = 10)

        #=== GPS Finder ===#
        self.geolocator_label = customtkinter.CTkLabel(self.scroll, text = "Find your location on GPS\nOnly try if on wifi", justify = "left")
        self.geolocator_label.grid(row = 1, column = 0, sticky = "w", padx = 10, pady = 5)
        self.geolocator_label_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "e.g.: New York City, New York", width = 180)
        self.geolocator_label_entry.grid(row = 2, column = 0, sticky = "w", padx = 10, pady = 5)

        Geo_button = customtkinter.CTkButton(self.scroll, text = "FIND ME", command = self.gpsLocator)
        Geo_button.grid(row = 3, column = 0, columnspan = 2, sticky = "w", padx = 10, pady = 5)


        
        self.Advanced_pointing_box = customtkinter.CTkTextbox(self.scroll, width=440, height=200, state = "disabled")
        self.Advanced_pointing_box.grid(row = 7, column = 0, columnspan = 2, sticky = "w", padx = 10, pady = 5)

    def gpsLocator(self):
        try:
            lat, long = gps(self.geolocator_label_entry.get())
            text = f"Latitude: {lat}\nLongitude: {long}"
        except Exception as e:
            text = str(e)
        self.Advanced_pointing_box.configure(state = "normal")
        self.Advanced_pointing_box.delete("0.0", "end")
        self.Advanced_pointing_box.insert("0.0", text)   
        self.Advanced_pointing_box.configure(state = "disabled")

    def calculate(self):
        try:
            now = datetime.datetime.now()

            self.results = pointing(
                latitude = float(self.latitude_entry.get()),
                longitude = float(self.longitude_entry.get()),
                year = now.year,
                month = now.month,
                day = now.day,
                hour = now.hour,
                minute = now.minute,
                delay = float(self.delay_entry.get()),
                num_points = int(self.num_points_entry.get()),
                lat_increment = float(self.latitude_increment_entry.get()),
                long_increment = float(self.longitude_increment_entry.get()),
            )
        
            self.AzAlt = azalt(self.results)
            
            self.AzAlt_box.configure(state = "normal")
            self.AzAlt_box.delete("0.0", "end")
            self.AzAlt_box.insert("0.0", self.AzAlt)   
            self.AzAlt_box.configure(state = "disabled")
        except ValueError as e:
            self.AzAlt_box.configure(state = "normal")
            self.AzAlt_box.delete("0.0", "end")
            self.AzAlt_box.insert("0.0", f"Input error: {e}\nCheck that all fields are filled and formatted like the examples.")
            self.AzAlt_box.configure(state = "disabled")
        except Exception as e:
            self.AzAlt_box.configure(state = "normal")
            self.AzAlt_box.delete("0.0", "end")
            self.AzAlt_box.insert("0.0", f"Calculation error: {e}")
            self.AzAlt_box.configure(state = "disabled")


    def updateClock(self):

        # sets the clock label on the GUI to the current system time

        now = datetime.datetime.now()

        self.clock_label.configure(
            text=now.strftime("%Y-%m-%d %H:%M:%S")
        )
        self.after(1000, self.updateClock)
    
    def enableDefaults(self):

        # removes text in entrys and disables them
        #!!! this function does not apply default parameters. That is controlled by startCollection function

        if self.default_switch.get() =="on":

            self.frequency_start_entry.delete(0, "end")
            self.frequency_stop_entry.delete(0, "end")
            self.integration_scans_entry.delete(0, "end")
            self.integration_time_entry.delete(0, "end")
            self.frequency_start_entry.configure(state="disabled", placeholder_text="1415", fg_color=("gray80", "gray10"))
            self.frequency_stop_entry.configure(state="disabled", placeholder_text="1425", fg_color=("gray80", "gray10"))
            self.integration_scans_entry.configure(state="disabled", placeholder_text="10", fg_color=("gray80", "gray10"))
            self.integration_time_entry.configure(state="disabled", placeholder_text="5", fg_color=("gray80", "gray10"))
            self.log("Using default parameters")
        else:
            self.frequency_start_entry.configure(state="normal", placeholder_text="1415", fg_color=("white", "gray21"))
            self.frequency_stop_entry.configure(state="normal", placeholder_text="1425", fg_color=("white", "gray21"))
            self.integration_scans_entry.configure(state="normal", placeholder_text="10", fg_color=("white", "gray21"))
            self.integration_time_entry.configure(state="normal", placeholder_text="5", fg_color=("white", "gray21"))

    
    def startCollection(self):

        # checks for default switch and returns either default values or text in the entry boxes
        # if default switch is off, data in the entry boxes is collected and is then checked to make sure its valid
        # a cfg dictionary is then created along with the other entrys in the GUI.  !!! The other entries are checked in the observationSession class as typos are not critical. 
        # The cfg is then passed to the observation session Class

        if self.session and self.session.is_alive():
            messagebox.showwarning(
                "Observation Running",
                "Stop the current observation before starting another.")
            return

        if self.default_switch.get() == "on":
            self.freq_i = float(self.default_freq_i)
            self.freq_f = float(self.default_freq_f)
            self.int_time = float(self.default_int_time)
            self.nint = int(self.default_nint)
            
        else:
            try:
                self.freq_i = float(self.frequency_start_entry.get())
                self.freq_f = float(self.frequency_stop_entry.get())
                self.int_time = float(self.integration_time_entry.get())
                self.nint = int(self.integration_scans_entry.get())
            except ValueError:
                messagebox.showerror(
                    "Invalid Input",
                    "Frequency, integration time, and integrations per scan must be numeric."
                )
                return
            
            if self.freq_i <= 0:
                messagebox.showerror(
                    "Invalid Frequency",
                    "Start frequency must be greater than zero."
                )
                return

            if self.freq_f <= self.freq_i:
                messagebox.showerror(
                    "Invalid Frequency",
                    "Stop frequency must be greater than start frequency."
                )
                return

            if self.int_time <= 0:
                messagebox.showerror(
                    "Invalid Integration Time",
                    "Integration time must be greater than zero."
                )
                return

            if self.nint <= 0:
                messagebox.showerror(
                    "Invalid Integrations",
                    "Integrations per scan must be greater than zero."
                )
                return
        try:

            latitude = (
                float(self.latitude_entry.get())
                if self.latitude_entry.get().strip()
                else None
            )

            longitude = (
                float(self.longitude_entry.get())
                if self.longitude_entry.get().strip()
                else None
            )

            altitude = (
                float(self.altitude_entry.get())
                if self.altitude_entry.get().strip()
                else None
            )

            azimuth = (
                float(self.azimuth_entry.get())
                if self.azimuth_entry.get().strip()
                else None
            )

        except ValueError:

            messagebox.showerror(
                "Invalid data",
                "Latitude, longitude, altitude, and azimuth must be numeric."
            )
            return

        args = Namespace(
            observer=self.observer_name_entry.get(),
            location=self.location_entry.get(),
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            azimuth=azimuth,
            description=self.description_entry.get("1.0", "end").strip(),

            freq_i=self.freq_i,
            freq_f=self.freq_f,

            df=1.0,

            veclength=1024,
            samp_rate=2.0,

            #int_length=100, #ignored when int_time is supplied
            int_time=self.int_time,

            nint=self.nint,

            biasT=self.bias_switch.get() == "on",

            data_dir=None,

            sleep_time=5.0,

            #causes a single sweep, ignore
            scan_period=0.001,
            total_time=0.001
        )


        self.startLogCapture()
        cfg = buildConfig(args, self.log)
        self.last_data_dir = cfg["data_dir"]
        self.stop_event = threading.Event()
        self.session = threading.Thread(
            target=runObservation,
            args=(cfg, self.log, self.stop_event),
            daemon=True
        )
        self.session.start()
        time.sleep(0.2)    #wait for GNU Radio logs
        self.stopLogCapture()
        self.plotObservation()

    def stopCollection(self):

        #sends a command to stop data collection 

        if not self.session or not self.session.is_alive():
            self.log("Data collection hasn't started")
            return

        if self.stop_event:
            self.stop_event.set()

        self.log("Stopping observation...\nWaiting for current frequency scan to finish...")

    def plotObservation(self):

        if self.session is None:
            return
        
        if self.session.is_alive():
            self.after(1000, self.plotObservation)

        else:
            if not self.last_data_dir:
                self.log("No observation data found.")
                return
            
            if not glob.glob(os.path.join(self.last_data_dir, "*.dat")):
                self.log("No data files found - skipping plot.")
                return

            self.log("Creating plot with corrections...")

            d, m = chart.analysis.read_run(directory=self.last_data_dir)

            d = np.array(d)

            nchans = m[0]["vector_length"]

            levels = np.median(
                d[:, :, nchans // 4:(-nchans // 4)],
                axis=(1, 2)
            )

            rescaled = d / levels.reshape(-1, 1, 1)

            bp = np.median(rescaled, axis=(0, 1))

            spectra = []
            freqs = []

            nremove = nchans // 16

            for scan_data, metadata in zip(d, m):

                spectrum = np.mean(scan_data, axis=0) / bp
                spectrum = 10 * np.log10(spectrum)

                spectrum = spectrum[nremove:-nremove]

                frequencies = (
                    (np.arange(metadata["vector_length"])
                    - metadata["vector_length"] / 2)
                    * metadata["samp_rate"]
                    / metadata["vector_length"]
                    + metadata["frequency"]
                )

                frequencies = 1e-9 * frequencies[nremove:-nremove]

                spectra.append(spectrum)
                freqs.append(frequencies)

            for k in range(len(spectra) - 1):

                spec1 = spectra[k]
                spec2 = spectra[k + 1]

                freq1 = freqs[k]
                freq2 = freqs[k + 1]

                ncommon = np.sum([1 if f in freq2 else 0 for f in freq1])

                if ncommon > 0:
                    spec2 += (
                        np.median(spec1[-ncommon:])
                        - np.median(spec2[:ncommon])
                    )

                    spectra[k + 1] = spec2

            plt.figure(figsize=(8, 4))

            for f, s in zip(freqs, spectra):
                plt.plot(f, s)

            plt.xlabel("Frequency [GHz]")
            plt.ylabel("[dB]")
            plt.title(os.path.basename(self.last_data_dir))

            plt.tight_layout()
            plt.show()


    def jupyter_local(self):

        #starts a single jupyter server in a subprocess.

        if self.jupyter_proc is None or self.jupyter_proc.poll() is not None:
            self.jupyter_proc = subprocess.Popen(["jupyter", "notebook", "--notebook-dir=~"],)
            self.log("Local Jupyter server started!")

    def jupyter_upload(self):
        webbrowser.open_new('https://radiolab.winona.edu/')


    def toggleDarkMode(self):

        if self.mode_switch.get() == "on":
            customtkinter.set_appearance_mode("Dark")
            self.log("DarkMode enabled!")
        else: customtkinter.set_appearance_mode("Light")
    
    def biasTwarn(self):

        # displays a warning message if BiasT is enabled
        # !!! This function does not enable BiasT. Instead the startCollection() function passes along the value for the switch, which is then enabled when the data collection is started.

        if self.bias_switch.get() == "on":
            messagebox.showwarning('WARNING', 'Only have this on if you know FOR SURE the BIAS-T is being used. \nIf you are following the CHART tutorial with the recommended LNA, it should be ON')

            self.log("Bias-T will be enabled!")

    def onClose(self):

        # defines a safe shutdown procedure that closes all subprocesses before exiting the GUI

        if self.jupyter_proc is not None:
            self.jupyter_proc.terminate()
        self.destroy()

    def startLogCapture(self):
        self._log_pipe_r, self._log_pipe_w = os.pipe()

        self._stdout_saved = os.dup(1)
        self._stderr_saved = os.dup(2)

        os.dup2(self._log_pipe_w, 1)
        os.dup2(self._log_pipe_w, 2)

        os.close(self._log_pipe_w)

        def reader():
            while True:
                data = os.read(self._log_pipe_r, 4096)
                if not data:
                    break
                for line in data.decode(errors="ignore").splitlines():
                    self.log(line)

        threading.Thread(target=reader, daemon=True).start()
    
    def stopLogCapture(self):
        if self._stdout_saved is None:
            return

        os.dup2(self._stdout_saved, 1)
        os.dup2(self._stderr_saved, 2)

        os.close(self._stdout_saved)
        os.close(self._stderr_saved)
    


if __name__ == "__main__":

    app = ChartApp()
    app.mainloop()
           