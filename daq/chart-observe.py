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
from tkinter import messagebox
import re
import threading
import numpy as np
import time
import chart


class ObservationSession:

    def __init__(self, config, logger):

        self.log = logger
        self.running = False
        self.tb = None

        self.cfg = config

        self.cfg["observer"] = self.clean(config.get("observer", ""))
        self.cfg["location"] = self.clean(config.get("location", ""))
        self.cfg["latitude"] = self.clean(config.get("latitude", ""))
        self.cfg["longitude"] = self.clean(config.get("longitude", ""))
        self.cfg["altitude"] = self.clean(config.get("altitude", ""))
        self.cfg["azimuth"] = self.clean(config.get("azimuth", ""))
        self.cfg["description"] = self.clean(config.get("description", ""))

        self.cfg["freq_i"] = float(config["freq_i"])
        self.cfg["freq_f"] = float(config["freq_f"])
        self.cfg["df"] = float(config["df"])
        self.cfg["scan_period"] = float(config["scan_period"])
        self.cfg["total_time"] = float(config["total_time"])
        self.cfg["veclength"] = int(config["veclength"])
        self.cfg["samp_rate"] = float(config["samp_rate"])
        self.cfg["int_length"] = int(config["int_length"])
        self.cfg["nint"] = int(config["nint"])
        self.cfg.setdefault("bias_t", False)
        self.cfg.setdefault("data_dir", "./data")

    def clean(self, value):
        if value is None:
            return ""
        return re.sub(r'[^A-Za-z0-9_-]', '', str(value))
    
    
    def stop(self):
        self.running = False

    
    def run(self):

        self.running = True

        self.tb = chart.blocks.TopBlock(
            c_freq=self.cfg["freq_i"],
            veclength=self.cfg["veclength"],
            samp_rate=self.cfg["samp_rate"],
            int_length=self.cfg["int_length"],
            nint=self.cfg["nint"],
            bias=self.cfg["bias_t"],
            data_dir=self.cfg["data_dir"],
            metadata=self.cfg
        )

        start = time.time()
        scan_index = 0

        while self.running and (time.time() - start < self.cfg["total_time"]):

            self.log(f"Scan {scan_index}")

            for f in np.arange(self.cfg["freq_i"],
                            self.cfg["freq_f"],
                            self.cfg["df"]):

                if not self.running:
                    break

                self.log(f"{f/1e6:.3f} MHz")

                self.tb.set_c_freq(f)
                self.tb.blocks_head_0.reset()
                self.tb.set_filename()

                self.tb.start()
                self.tb.wait()

                self.tb.meta_save()

            scan_index += 1
            time.sleep(self.cfg["scan_period"])

        self.log("Observation complete")

        if self.tb:
            del self.tb




class ChartApp(customtkinter.CTk):

    def __init__(self):
        super().__init__()

        self.session = None
    
        self.data_directory = None
        self.bias_t = False

        self.default_freq_i = "1415"
        self.default_freq_f = "1425"
        self.default_int_time = "5"
        self.default_nint = "10"

        self.buildWindow()
        self.buildWidgets()

    def buildWindow(self):

        customtkinter.set_appearance_mode("light")
        customtkinter.set_default_color_theme("blue")

        self.geometry("786x480")
        self.title("CHART Data Collection")

        self.protocol(
            "WM_DELETE_WINDOW",
            self.onClose
        )
    
    def buildWidgets(self):  #set up GUI and call widgets

        self.mode_switch = customtkinter.CTkSwitch(self, text="Dark Mode", command=self.toggleDarkMode, onvalue="on", offvalue="off")
        self.mode_switch.grid(column=0, row=0, padx=10, pady=2, sticky="NW")

        self.time_button = customtkinter.CTkButton(self, text="Set System DateTime", command=self.openTimeWindow)
        self.time_button.grid(column=0, row=0, padx=10, pady=2, sticky="N")

        self.clock_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.clock_frame.grid(column=0, row=0, padx=2, pady=2, sticky="NE")
        self.clock_label_description = customtkinter.CTkLabel(self.clock_frame, text="Observation Time: ")
        self.clock_label_description.grid(column=0, row=0, padx=2, pady=2, sticky="E")
        self.clock_label = customtkinter.CTkLabel(self.clock_frame, text="")
        self.clock_label.grid(column=2, row=0, padx=2, pady=2, sticky="W")
        self.updateClock()

        self.rowconfigure(2, weight=0)
        self.rowconfigure(1, weight=1)   # defines what rows can expand
        self.rowconfigure(0, weight=0)
        self.columnconfigure(0, weight=1)

        self.scroll_frame = customtkinter.CTkScrollableFrame(self)
        self.scroll_frame.grid(column=0, row=1, padx=10, pady=0, sticky="nsew")
        self.scroll_frame.columnconfigure(1, weight=1)
        self.scroll_frame.columnconfigure(3, weight=1)

        self.terminal = customtkinter.CTkTextbox(self, height=80)
        self.terminal.grid(row=2, column=0, sticky="ew", padx=10, pady=(0,10))
        self.terminal.configure(state="disabled")

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

        self.jupyter_upload_button = customtkinter.CTkButton(self.scroll_frame, text="Upload to Jupyter Hub")
        self.jupyter_upload_button.grid(column=2, row=9, padx=10, pady=3, sticky="new")

        self.jupyter_local_button = customtkinter.CTkButton(self.scroll_frame, text="Local Jupyter Notebook")
        self.jupyter_local_button.grid(column=3, row=9, padx=10, pady=3, sticky="new")
    
    def log(self, message):

        self.terminal.configure(state="normal")
        self.terminal.insert(
            "end",
            f"{message}\n"
        )
        self.terminal.see("end")
        self.terminal.configure(state="disabled")
    
    def submitTime(self):

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
        self.popup = customtkinter.CTkToplevel(self)
        self.popup.title("System Date and Time")
        self.popup.geometry("240x200")
        self.popup.columnconfigure(1, weight=1)
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

        self.popup.wait_visibility()
        self.popup.focus()
        self.popup.grab_set()

    def updateClock(self):
        now = datetime.datetime.now()

        self.clock_label.configure(
            text=now.strftime("%Y-%m-%d %H:%M:%S")
        )
        self.after(1000, self.updateClock)
    
    def enableDefaults(self):
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

        if self.default_switch.get() == "on":
            freq_i = float(self.default_freq_i)
            freq_f = float(self.default_freq_f)
            int_length = int(self.default_int_time)
            nint = int(self.default_nint)
            
        else:
            try:
                freq_i = float(self.frequency_start_entry.get())
                freq_f = float(self.frequency_stop_entry.get())
                int_length = int(self.integration_time_entry.get())
                nint = int(self.integration_scans_entry.get())
            except ValueError:
                messagebox.showerror(
                    "Invalid Input",
                    "Frequency, integration time, and integrations per scan must be numeric."
                )
                return
            
            if freq_i <= 0:
                messagebox.showerror(
                    "Invalid Frequency",
                    "Start frequency must be greater than zero."
                )
                return

            if freq_f <= freq_i:
                messagebox.showerror(
                    "Invalid Frequency",
                    "Stop frequency must be greater than start frequency."
                )
                return

            if int_length <= 0:
                messagebox.showerror(
                    "Invalid Integration Time",
                    "Integration time must be greater than zero."
                )
                return

            if nint <= 0:
                messagebox.showerror(
                    "Invalid Integrations",
                    "Integrations per scan must be greater than zero."
                )
                return

        cfg = {
            "observer": self.observer_name_entry.get(),
            "location": self.location_entry.get(),
            "latitude": self.latitude_entry.get(),
            "longitude": self.longitude_entry.get(),
            "altitude": self.altitude_entry.get(),
            "azimuth": self.azimuth_entry.get(),
            "description": self.description_entry.get("1.0", "end"),

            "freq_i": self.freq_i * 1e6,
            "freq_f": self.freq_f * 1e6,
            "df": 1.0,
            "scan_period": float(self.default_int_time),
            "total_time": 60,
            "veclength": 1024,
            "samp_rate": 2e6,
            "int_length": float(self.int_length),
            "nint": int(self.nint),
            "bias_t": self.bias_switch.get() == "on",
            "data_dir": self.data_directory or "./data"
        }

        self.session = ObservationSession(cfg, self.log)
        threading.Thread(target=self.session.run, daemon=True).start()

    def stopCollection(self):
        if self.session:
            self.session.stop()

    def toggleDarkMode(self):
        if self.mode_switch.get() == "on":
            customtkinter.set_appearance_mode("Dark")
            self.log("DarkMode enabled!")
        else: customtkinter.set_appearance_mode("Light")
    
    def biasTwarn(self):
        if self.bias_switch.get() == "on":
            messagebox.showwarning('WARNING', 'Only have this on if you know FOR SURE the BIAS-T is being used. \nIf you are following the CHART tutorial with the recommended LNA, it should be ON')
    
    def onClose(self):
        # self.collector.stop()
        self.destroy()




if __name__ == "__main__":

    app = ChartApp()
    app.mainloop()
           
           