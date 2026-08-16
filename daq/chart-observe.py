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
import socket
import matplotlib.pyplot as plt

from tkinter import messagebox
from argparse import Namespace
from freq_and_time_scan import buildConfig, runObservation
from chart.azalt import pointing, azalt, gps, gimme_time, altitude_plot_data

# Live waterfall display.  WaterfallPanel and the display constants are reused
# unchanged from the standalone live_view tool; only the producer wiring is
# re-implemented here because chart-observe already owns the science thread.
import queue
from chart.live_view import (
    WaterfallPanel,
    LiveViewWorker,
    CENTER_FREQ,
    GUI_POLL_MS,
    RESIZE_REDRAW_MS,
    QUEUE_MAXDEPTH,
)

class ChartApp(customtkinter.CTk):

    def __init__(self):
        super().__init__()

        self.session = None     # Data collection thread is stored here
        self.jupyter_proc = None    # jupyter local subprocess
        self.last_data_dir = None   # stores last directory created for plotting function
        self.popup = None       # allows checking for multiple date and time popup windows

        # --- Live display state -------------------------------------------
        # The science thread (self.session) feeds spectra to the Display tab
        # through this queue.  A separate producer thread polls the GNU Radio
        # probe once the TopBlock exists; the GUI drains the queue on a timer.
        self.spectrum_queue   = queue.Queue(maxsize=QUEUE_MAXDEPTH)
        self.display_tb       = None    # live TopBlock, handed over by on_tb_ready
        self.display_tb_ready = None    # threading.Event, set when tb available
        self.display_stop     = None    # threading.Event to halt the producer
        self.display_producer = None    # producer thread handle
        self.waterfall        = None    # WaterfallPanel, built in buildDisplayTab
        self.frames_drawn     = 0
        self.display_last_freq = None   # last freq the waterfall axis was set to
        self.display_poll_id  = None    # after() id for the queue-drain loop

        # Monitor (standalone live view) state.  Mutually exclusive with a
        # science sweep — both drive the same waterfall through spectrum_queue,
        # but only one can hold the SDR at a time.
        self.monitor_worker = None      # LiveViewWorker instance when active
        self._last_display_state = "idle"   # for detecting state transitions

        #storage for stdout/stderr pipe required to capture GNU radio messages 
        self._log_pipe_r = None
        self._log_pipe_w = None
        self._stdout_saved = None
        self._stderr_saved = None

        self.default_freq_i = "1415"
        self.default_freq_f = "1425"
        self.default_int_time = "5"
        self.default_nint = "10"
        #Making sure the pointing calculator and advanced pointing values persist after closing their respective windows

        self.advanced_window = None
        self.pointing_window = None

        self.buildWindow()
        self.buildWidgets()

    def buildWindow(self):

        #builds main GUI window and captures when GUI is closed

        customtkinter.set_appearance_mode("light")
        customtkinter.set_default_color_theme("blue")
        customtkinter.set_widget_scaling(0.98)

        self.geometry("786x510")
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
        
        self.mode_switch = customtkinter.CTkSwitch(self.top_bar, text="Dark Mode", command=self.toggleDarkMode, onvalue="on", offvalue="off", corner_radius=0)
        self.mode_switch.grid(column=0, row=0, padx=10, pady=2, sticky="w")
        
        self.button_frame = customtkinter.CTkFrame(self.top_bar, fg_color="transparent")
        self.button_frame.grid(column=1, row=0, pady=2)   # centered in its column
        
        self.pointing_button = customtkinter.CTkButton(self.button_frame, text="Pointing Calculator", width=160, command=self.openPointingCalculator, hover_color = "purple", corner_radius=0)
        self.pointing_button.grid(column=0, row=0, padx=5)
        
        self.time_button = customtkinter.CTkButton(self.button_frame, text="Set System DateTime", width=160, command=self.openTimeWindow, corner_radius=0)
        self.time_button.grid(column=1, row=0, padx=5)
        
        self.clock_frame = customtkinter.CTkFrame(self.top_bar, fg_color="transparent")
        self.clock_frame.grid(column=2, row=0, padx=2, pady=2, sticky="e")
        self.clock_label_description = customtkinter.CTkLabel(self.clock_frame, text="Observation Time: ")
        self.clock_label_description.grid(column=0, row=0, padx=2, pady=2, sticky="e")
        self.clock_label = customtkinter.CTkLabel(self.clock_frame, text="")
        self.clock_label.grid(column=1, row=0, padx=2, pady=2, sticky="w")
        self.updateClock()

        # Global recording indicator — always visible regardless of tab, so the
        # user knows a scan is in progress even from the Configuration tab.
        # Sits just under the clock.  Driven by pollDisplayQueue.
        self.record_indicator = customtkinter.CTkLabel(
            self.clock_frame, text="\u25cf  Idle",
            text_color=("gray60", "gray50"),
        )
        self.record_indicator.grid(column=0, row=1, columnspan=2, padx=2,
                                   pady=(0, 2), sticky="e")

        # defines what rows can expand
        # row 0: top bar (fixed)   row 1: body/tabview (expands)
        # row 2: control strip (fixed)   row 3: terminal (fixed)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.columnconfigure(0, weight=1)

        # --- Body tabview (row 1) -----------------------------------------
        # Two tabs: "Configuration" holds the existing settings (the scroll
        # frame, unchanged) and "Display" will hold the live waterfall.
        # The tabview is the expanding region; the control strip and terminal
        # below it stay persistent across both tabs.
        self.tabview = customtkinter.CTkTabview(self, corner_radius=0)
        self.tabview.grid(column=0, row=1, padx=10, pady=0, sticky="nsew")
        self.tab_config  = self.tabview.add("Configuration")
        self.tab_display = self.tabview.add("Display")

        # The scroll frame now lives inside the Configuration tab.  Keeping the
        # name self.scroll_frame unchanged means every widget parented to it
        # (buildEntries, buildSwitches, buildButtons, ...) works untouched —
        # only the parent changed, from self to the tab.
        self.scroll_frame = customtkinter.CTkScrollableFrame(self.tab_config, corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True)
        self.scroll_frame.columnconfigure(1, weight=1)
        self.scroll_frame.columnconfigure(3, weight=1)

        # --- Persistent control strip (row 2) -----------------------------
        # A fixed-height band that always stays visible (never scrolls), set
        # off from the body above by a thin separator line.  Start/Stop live
        # here so the primary actions are reachable no matter what the body
        # is showing.  Colours come from the active theme so dark mode is
        # honoured automatically.
        self.control_strip = customtkinter.CTkFrame(self, corner_radius=0,
                                                    fg_color="transparent")
        self.control_strip.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 2))
        # Column weights for the strip's contents are set in buildButtons,
        # which owns the sweep-button / monitor-group layout.

        # Thin separator across the top of the strip: a 1px frame using a
        # theme-aware colour tuple (light_mode, dark_mode) so it flips with
        # the appearance mode.  Spans both button columns.
        self.control_separator = customtkinter.CTkFrame(
            self.control_strip, height=1, corner_radius=0,
            fg_color=("gray70", "gray30"),
        )
        self.control_separator.grid(row=0, column=0, columnspan=6,
                                    sticky="ew", pady=(0, 5))

        self.terminal = customtkinter.CTkTextbox(self, height=80, corner_radius=0, border_width=3, border_color="gray")
        self.terminal.grid(row=3, column=0, sticky="ew", padx=10, pady=(0,10))
        self.terminal.configure(state="disabled")

        #widgets inside of the scroll frame is called with the following functions
        self.buildEntries()
        self.buildSwitches()
        self.buildButtons()

        # Display tab contents (status line, parameter summary, waterfall)
        self.buildDisplayTab()

        # functions that start at runtime are here
        self.loadSettings()
        self.gpsDisable()
        self.syncControlStates()   # set initial sweep/monitor control states

        # Start the queue-drain loop for the live waterfall.  Runs continuously;
        # it simply finds an empty queue when no observation is active.
        self.display_poll_id = self.after(GUI_POLL_MS, self.pollDisplayQueue)

        # Separate slow timer that redraws the waterfall's static background
        # (axes/ticks/colorbar) after a resize or frequency-axis change.  Kept
        # off the data path so an expensive redraw never delays a spectrum.
        self.display_resize_id = self.after(RESIZE_REDRAW_MS, self.checkDisplayResize)
    
    def buildEntries(self):


        #left side
        #frame for saved settings
        self.saved_settings_frame = customtkinter.CTkFrame(self.scroll_frame, border_color="gray", border_width=3, corner_radius=0)
        self.saved_settings_frame.grid(column=0, row=0, padx=5, pady=10, rowspan=6, columnspan=2, sticky="NEWS")
        self.saved_settings_frame.columnconfigure(0, weight=1)
        self.saved_settings_frame.columnconfigure(1, weight=1)

        self.observer_name_label = customtkinter.CTkLabel(self.saved_settings_frame, text="Observer Name")
        self.observer_name_label.grid(column=0, row=0, padx=10, pady=7, sticky="e")
        self.observer_name_entry = customtkinter.CTkEntry(self.saved_settings_frame, placeholder_text="Enter Here", corner_radius=0)
        self.observer_name_entry.grid(column=1, row=0, padx=10, pady=(10,7), sticky="sew")

        self.location_label = customtkinter.CTkLabel(self.saved_settings_frame, text="Location")
        self.location_label.grid(column=0, row=1, padx=10, pady=0, sticky="ne")
        self.location_entry = customtkinter.CTkEntry(self.saved_settings_frame, placeholder_text="e.g.: Winona, Minnesota", corner_radius=0)
        self.location_entry.grid(column=1, row=1, padx=10, pady=0, sticky="nwe")

        self.latitude_label = customtkinter.CTkLabel(self.saved_settings_frame, text="Latitude (deg)")
        self.latitude_label.grid(column=0, row=3, padx=10, pady=7, sticky="e")
        self.latitude_entry = customtkinter.CTkEntry(self.saved_settings_frame, placeholder_text="Enter or Calculate", corner_radius=0)
        self.latitude_entry.grid(column=1, row=3, padx=10, pady=7, sticky="ew")

        self.longitude_label = customtkinter.CTkLabel(self.saved_settings_frame, text="Longitude (deg)")
        self.longitude_label.grid(column=0, row=4, padx=10, pady=0, sticky="ne")
        self.longitude_entry = customtkinter.CTkEntry(self.saved_settings_frame, placeholder_text="Enter or Calculate", corner_radius=0)
        self.longitude_entry.grid(column=1, row=4, padx=10, pady=(0,5), sticky="nwe")



        self.altitude_label = customtkinter.CTkLabel(self.scroll_frame, text="Altitude (deg)")
        self.altitude_label.grid(column=0, row=6, padx=10, pady=5, sticky='e')
        self.altitude_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="Enter Here", corner_radius=0)
        self.altitude_entry.grid(column=1, row=6, padx=10, pady=5, sticky="ew")

        self.azimuth_label = customtkinter.CTkLabel(self.scroll_frame, text="Azimuth (deg)")
        self.azimuth_label.grid(column=0, row=7, padx=10, pady=5, sticky="en")
        self.azimuth_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="Enter Here", corner_radius=0)
        self.azimuth_entry.grid(column=1, row=7, padx=10, pady=5, sticky="nwe")

        self.description_label = customtkinter.CTkLabel(self.scroll_frame, text="Description (optional)")
        self.description_label.grid(column=0, row=8, padx=10, sticky="new")
        self.description_entry = customtkinter.CTkTextbox(self.scroll_frame, height=65, corner_radius=0)
        self.description_entry.grid(column=0, row=9, padx=10, pady=0, sticky="new", columnspan=2, rowspan=2)


        #adding in a real time monitor of lat and long for the pointing calculator, this will auto input the lat and long from the main menu to the pointing calculator menu
        self.latitude_entry.bind("<KeyRelease>",  lambda e: self.syncCoords(self.latitude_entry,  "pointing_latitude_entry"))
        self.latitude_entry.bind("<FocusOut>",    lambda e: self.syncCoords(self.latitude_entry,  "pointing_latitude_entry"))
        self.longitude_entry.bind("<KeyRelease>", lambda e: self.syncCoords(self.longitude_entry, "pointing_longitude_entry"))
        self.longitude_entry.bind("<FocusOut>",   lambda e: self.syncCoords(self.longitude_entry, "pointing_longitude_entry"))
        #sync coords is defined above the open pointing calculator definition


        #right side
        self.frequency_label = customtkinter.CTkLabel(self.scroll_frame, text="Frequency Scan Setup", font=("Arial", 18, "bold")   )
        self.frequency_label.grid(column=2, row=0, padx=10, pady=5, sticky="we", columnspan=2)

        self.frequency_start_label = customtkinter.CTkLabel(self.scroll_frame, text="Start Frequency (MHz)")
        self.frequency_start_label.grid(column=2, row=3, padx=10, pady=5, sticky="e")
        self.frequency_start_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="1415", corner_radius=0)
        self.frequency_start_entry.grid(column=3, row=3, padx=10, pady=5, sticky="ew")

        self.frequency_stop_label = customtkinter.CTkLabel(self.scroll_frame, text="Stop Frequency (MHz)")
        self.frequency_stop_label.grid(column=2, row=4, padx=10, pady=5, sticky="en")
        self.frequency_stop_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="1425", corner_radius=0)
        self.frequency_stop_entry.grid(column=3, row=4, padx=10, pady=5, sticky="nwe")

        self.integration_time_label = customtkinter.CTkLabel(self.scroll_frame, text="Integration time (s)")
        self.integration_time_label.grid(column=2, row=5, padx=10, pady=5, sticky="en")
        self.integration_time_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="5", corner_radius=0)
        self.integration_time_entry.grid(column=3, row=5, padx=10, pady=5, sticky="nwe")

        self.integration_scans_label = customtkinter.CTkLabel(self.scroll_frame, text="Integrations per scan step")
        self.integration_scans_label.grid(column=2, row=6, padx=10, pady=5, sticky="ne")
        self.integration_scans_entry = customtkinter.CTkEntry(self.scroll_frame, placeholder_text="10", corner_radius=0)
        self.integration_scans_entry.grid(column=3, row=6, padx=10, pady=5, sticky="nwe")

        self.frequency_start_entry.bind("<KeyRelease>", self.updateTimeEstimate)
        self.frequency_stop_entry.bind("<KeyRelease>", self.updateTimeEstimate)
        self.integration_time_entry.bind("<KeyRelease>", self.updateTimeEstimate)
        self.integration_scans_entry.bind("<KeyRelease>", self.updateTimeEstimate)

        self.estimated_time_label = customtkinter.CTkLabel(self.scroll_frame, text="")
        self.estimated_time_label.grid(column=3, row=7, padx=10, pady=5, sticky="w")

    # ======================================================================
    # Live Display tab
    # ======================================================================

    def buildDisplayTab(self):
        """Build the Display tab: status line, parameter summary, waterfall.

        Layout: the tab is split left/right — a parameter summary panel on the
        left and the waterfall on the right.  The summary itself contains two
        groups (observer info, SDR/scan settings); whether those groups stack
        vertically (compact) or sit side by side (mirroring Configuration) is
        controlled by a single knob below — see SETTINGS_PLACEMENT.
        """
        tab = self.tab_display

        # === TUNABLE KNOBS ================================================
        # Width ratio of summary vs waterfall.  weights are relative ints, so
        # 1:2 gives the waterfall ~2/3 of the width.  Bump WATERFALL_WEIGHT to
        # 3 for ~3/4, etc.
        SUMMARY_WEIGHT   = 1
        WATERFALL_WEIGHT = 2

        # How the two summary groups are arranged:
        #   "stacked"    → settings below observer  (compact, one narrow column)
        #   "side"       → settings right of observer (two columns, mirrors the
        #                  Configuration tab's geography)
        SETTINGS_PLACEMENT = "stacked"
        # ==================================================================

        # Outer grid: row 0 = status (full width), row 1 = body (expands).
        tab.rowconfigure(0, weight=0)
        tab.rowconfigure(1, weight=1)
        tab.columnconfigure(0, weight=SUMMARY_WEIGHT)    # summary panel
        tab.columnconfigure(1, weight=WATERFALL_WEIGHT)  # waterfall

        # --- Status line: indicator dot + state + tuning + rate -----------
        # Spans both columns across the top.
        status_row = customtkinter.CTkFrame(tab, fg_color="transparent")
        status_row.grid(row=0, column=0, columnspan=2, sticky="ew",
                        padx=6, pady=(6, 2))

        # Unicode filled circle; colour flips green (active) / gray (idle).
        self.display_dot = customtkinter.CTkLabel(
            status_row, text="\u25cf", width=18,
            text_color=("gray60", "gray50"),
        )
        self.display_dot.grid(row=0, column=0, padx=(2, 6))

        self.display_status = customtkinter.CTkLabel(status_row, text="Idle")
        self.display_status.grid(row=0, column=1, sticky="w")

        # --- Parameter summary panel (left) -------------------------------
        # sticky="new" keeps the params hugging the top-left of their column
        # rather than centering in the tall left cell.
        summary = customtkinter.CTkFrame(tab, border_color="gray",
                                         border_width=2, corner_radius=0)
        summary.grid(row=1, column=0, sticky="new", padx=6, pady=(2, 6))
        summary.columnconfigure(0, weight=1)

        # Two groups, each its own frame.  observer_frame always sits top-left;
        # settings_frame placement is the knob above.
        observer_frame = customtkinter.CTkFrame(summary, fg_color="transparent")
        settings_frame = customtkinter.CTkFrame(summary, fg_color="transparent")

        observer_frame.grid(row=0, column=0, sticky="new", padx=4, pady=4)
        if SETTINGS_PLACEMENT == "side":
            settings_frame.grid(row=0, column=1, sticky="new", padx=4, pady=4)
            summary.columnconfigure(1, weight=1)
        else:   # "stacked"
            settings_frame.grid(row=1, column=0, sticky="new", padx=4, pady=4)

        # Read-only value labels stored in a dict so updateDisplaySummary can
        # refresh them from the entry fields when an observation starts.
        self._summary_values = {}

        def add_row(parent, r, key, label_text):
            parent.columnconfigure(1, weight=1)
            lbl = customtkinter.CTkLabel(parent, text=label_text, anchor="e")
            lbl.grid(row=r, column=0, padx=(6, 4), pady=1, sticky="e")
            val = customtkinter.CTkLabel(parent, text="—", anchor="w")
            val.grid(row=r, column=1, padx=(4, 6), pady=1, sticky="w")
            self._summary_values[key] = val

        observer_cfg = (
            ("observer",  "Observer:"),
            ("location",  "Location:"),
            ("latitude",  "Latitude:"),
            ("longitude", "Longitude:"),
            ("altitude",  "Altitude:"),
            ("azimuth",   "Azimuth:"),
        )
        settings_cfg = (
            ("freq_i",   "Start Freq (MHz):"),
            ("freq_f",   "Stop Freq (MHz):"),
            ("int_time", "Integration (s):"),
            ("nint",     "Ints / step:"),
        )
        for r, (key, text) in enumerate(observer_cfg):
            add_row(observer_frame, r, key, text)
        for r, (key, text) in enumerate(settings_cfg):
            add_row(settings_frame, r, key, text)

        # --- Waterfall (right) --------------------------------------------
        wf_frame = customtkinter.CTkFrame(tab, corner_radius=0,
                                          fg_color="#1a1a2e")
        wf_frame.grid(row=1, column=1, sticky="nsew", padx=6, pady=(0, 6))
        self.waterfall = WaterfallPanel(wf_frame)

    def updateDisplaySummary(self):
        """Copy the current entry-field values into the Display tab summary.

        Called when an observation starts, so the front panel reflects what is
        actually being observed.  Reads the same entries the Configuration tab
        edits; shows a dash for blanks.
        """
        def txt(entry):
            v = entry.get().strip()
            return v if v else "—"

        self._summary_values["observer"].configure(text=txt(self.observer_name_entry))
        self._summary_values["location"].configure(text=txt(self.location_entry))
        self._summary_values["latitude"].configure(text=txt(self.latitude_entry))
        self._summary_values["longitude"].configure(text=txt(self.longitude_entry))
        self._summary_values["altitude"].configure(text=txt(self.altitude_entry))
        self._summary_values["azimuth"].configure(text=txt(self.azimuth_entry))
        # Scan settings come from the validated values set in startCollection.
        self._summary_values["freq_i"].configure(text=f"{self.freq_i:g}")
        self._summary_values["freq_f"].configure(text=f"{self.freq_f:g}")
        self._summary_values["int_time"].configure(text=f"{self.int_time:g}")
        self._summary_values["nint"].configure(text=f"{self.nint:g}")

    # --- Display producer (taps the science TopBlock) ---------------------

    def onDisplayTbReady(self, tb):
        """Callback handed to runObservation; receives the live TopBlock.

        Runs in the science thread.  Stashes tb and unblocks the producer.
        """
        self.display_tb = tb
        if self.display_tb_ready is not None:
            self.display_tb_ready.set()

    def displayProducerLoop(self):
        """Poll the TopBlock's display branch, push (freq, spectrum) to queue.

        Mirrors the producer loop proven in live_view, but lives here because
        chart-observe owns the science thread (self.session) directly.  Runs in
        its own thread so it can read the probe while the science thread is
        blocked in tb.wait().
        """
        if not self.display_tb_ready.wait(timeout=15.0):
            return
        tb = self.display_tb
        if tb is None:
            return

        last_vec = None
        while not self.display_stop.is_set():
            tb = self.display_tb
            if tb is None:
                break
            vec = tb.get_display_spectrum()
            if vec is not None:
                if last_vec is None or not np.array_equal(vec, last_vec):
                    if self.spectrum_queue.full():
                        try:
                            self.spectrum_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.spectrum_queue.put_nowait((tb.c_freq, vec.copy()))
                    last_vec = vec
            time.sleep(0.05)

    def startDisplayProducer(self):
        """Spin up the display tap for a newly started observation."""
        self.display_tb        = None
        self.display_tb_ready  = threading.Event()
        self.display_stop      = threading.Event()
        self.frames_drawn      = 0
        self.display_last_freq = None
        self.display_producer  = threading.Thread(
            target=self.displayProducerLoop, daemon=True,
            name="display-producer")
        self.display_producer.start()

    def stopDisplayProducer(self):
        """Signal the display tap to stop and drop its TopBlock reference."""
        if self.display_stop is not None:
            self.display_stop.set()
        if self.display_producer is not None:
            self.display_producer.join(timeout=2.0)
        self.display_tb = None

    def pollDisplayQueue(self):
        """Drain the spectrum queue into the waterfall (GUI thread, on timer).

        Always reschedules itself.  Draws spectra from whichever producer is
        active (science sweep or monitor) — the queue is source-agnostic.  Keeps
        the indicator, status line, and control enable/disable in sync with the
        current instrument state.
        """
        state = self.displayState()
        active = state in ("sweep", "monitor")

        # Only draw when the Display tab is actually visible.  Blitting to an
        # unmapped canvas (user on the Configuration tab) can corrupt the saved
        # background.  We still drain the queue so it can't back up; the frames
        # are simply discarded while hidden and drawing resumes on return.
        display_visible = self.tabview.get() == "Display"

        drained = 0
        while True:
            try:
                c_freq, spectrum = self.spectrum_queue.get_nowait()
            except queue.Empty:
                break
            if active and display_visible and self.waterfall is not None:
                if c_freq != self.display_last_freq:
                    self.waterfall.set_center_freq(c_freq)
                    self.display_last_freq = c_freq
                self.waterfall.push(spectrum)
                self.frames_drawn += 1
            drained += 1
            if drained >= 5:
                break

        # Re-sync the control widgets only when the state actually changes
        # (e.g. a sweep finishing on its own), to avoid reconfiguring widgets
        # every tick.
        if state != self._last_display_state:
            self.syncControlStates()
            self._last_display_state = state

        # Indicator: green = recording sweep, blue = monitoring, gray = idle.
        if state == "sweep":
            freq_str = (f"{self.display_last_freq / 1e6:.3f} MHz"
                        if self.display_last_freq else "tuning…")
            green = ("#2e7d32", "#66bb6a")
            self.display_dot.configure(text_color=green)
            self.display_status.configure(
                text=f"Observing — {freq_str}   |   {self.frames_drawn} frames")
            self.record_indicator.configure(text="\u25cf  Recording",
                                            text_color=green)
        elif state == "monitor":
            freq_str = (f"{self.display_last_freq / 1e6:.3f} MHz"
                        if self.display_last_freq else "tuning…")
            blue = ("#1565c0", "#42a5f5")
            self.display_dot.configure(text_color=blue)
            self.display_status.configure(
                text=f"Monitoring — {freq_str}   |   {self.frames_drawn} frames")
            self.record_indicator.configure(text="\u25cf  Monitoring",
                                            text_color=blue)
        else:  # idle
            gray = ("gray60", "gray50")
            self.display_dot.configure(text_color=gray)
            if self.frames_drawn > 0:
                self.display_status.configure(
                    text=f"Idle — last run drew {self.frames_drawn} frames")
            else:
                self.display_status.configure(text="Idle")
            self.record_indicator.configure(text="\u25cf  Idle", text_color=gray)

        self.display_poll_id = self.after(GUI_POLL_MS, self.pollDisplayQueue)

    def checkDisplayResize(self):
        """Slow timer: redraw the waterfall background when dirty.

        Only acts when the Display tab is visible — redrawing a hidden canvas
        is wasted work and can touch an unmapped widget.  Reschedules itself.
        """
        if (self.waterfall is not None
                and self.tabview.get() == "Display"):
            self.waterfall.redraw_background()
        self.display_resize_id = self.after(RESIZE_REDRAW_MS, self.checkDisplayResize)

    def buildSwitches(self):
        self.default_switch = customtkinter.CTkSwitch(self.scroll_frame, text="Use Default Parameters", onvalue="on", offvalue="off", command=self.enableDefaults, corner_radius=0)
        self.default_switch.grid(column=2, row=1, padx=10, pady=10, sticky="w")

        self.bias_switch = customtkinter.CTkSwitch(self.scroll_frame, text="Enable Bias-T", onvalue="on", offvalue="off", command=self.biasTwarn, corner_radius=0)
        self.bias_switch.grid(column=2, row=7, padx=10, pady=5, sticky="w")
    
    def buildButtons(self):
        # The persistent control strip holds two mutually-exclusive instrument
        # controls side by side: the science sweep (a single toggle button) and
        # the monitor (a live-view switch with its own tuning + LNA controls).
        # Start Sweep always takes priority — starting it stops the monitor.
        strip = self.control_strip

        # Columns: 0 sweep button | 1 divider | 2 "Monitor" switch |
        #          3 "Tune" label | 4 freq entry | 5 LNA checkbox
        strip.columnconfigure(0, weight=1)   # sweep button expands
        strip.columnconfigure(2, weight=0)
        strip.columnconfigure(4, weight=0)

        # Sweep toggle — replaces the old Start/Stop pair.  Text and colour
        # reflect state; the command routes to the toggle handler.
        self.sweep_button = customtkinter.CTkButton(
            strip, text="Start Sweep", command=self.toggleSweep, corner_radius=0)
        self.sweep_button.grid(column=0, row=1, padx=(0, 8), pady=2, sticky="ew")

        # Thin vertical divider between the sweep and monitor groups.
        # Fixed height (not sticky="ns") so it acts as a visual rule without
        # driving the strip's height.
        divider = customtkinter.CTkFrame(strip, width=2, height=28,
                                         corner_radius=0,
                                         fg_color=("gray70", "gray30"))
        divider.grid(column=1, row=1, padx=4, pady=2)

        # Monitor switch (live view, no recording).
        self.monitor_switch = customtkinter.CTkSwitch(
            strip, text="Monitor", command=self.toggleMonitor,
            onvalue="on", offvalue="off", corner_radius=0)
        self.monitor_switch.grid(column=2, row=1, padx=(8, 8), pady=2, sticky="w")

        # Monitor tuning entry, defaulting to the 21 cm line.
        self.monitor_tune_label = customtkinter.CTkLabel(strip, text="Tune (MHz):")
        self.monitor_tune_label.grid(column=3, row=1, padx=(4, 2), pady=2, sticky="e")
        self.monitor_freq_entry = customtkinter.CTkEntry(
            strip, width=80, corner_radius=0)
        self.monitor_freq_entry.insert(0, "1420.4")
        self.monitor_freq_entry.grid(column=4, row=1, padx=(0, 8), pady=2, sticky="w")

        # LNA power checkbox — kept in sync with the Configuration tab's
        # Bias-T switch and firing the same warning.
        self.monitor_lna_check = customtkinter.CTkCheckBox(
            strip, text="LNA power", command=self.monitorLnaToggled,
            onvalue="on", offvalue="off", corner_radius=0)
        self.monitor_lna_check.grid(column=5, row=1, padx=(0, 2), pady=2, sticky="w")

        self.jupyter_upload_button = customtkinter.CTkButton(self.scroll_frame, text="Upload to Jupyter Hub", command=self.jupyter_upload, corner_radius=0)
        self.jupyter_upload_button.grid(column=2, row=10, padx=10, pady=3, sticky="new")

        self.jupyter_local_button = customtkinter.CTkButton(self.scroll_frame, text="Local Jupyter Notebook", command=self.jupyter_local, corner_radius=0)
        self.jupyter_local_button.grid(column=3, row=10, padx=10, pady=3, sticky="new")


        self.save_button_frame = customtkinter.CTkFrame(self.saved_settings_frame, corner_radius=0, fg_color="transparent", bg_color="transparent")
        self.save_button_frame.grid(row=5, column=0, columnspan=2, pady=5)

        self.calculate_coordinates_button = customtkinter.CTkButton(self.save_button_frame, corner_radius=0, text="Calculate Coordinates", command=self.gpsLocator)
        self.calculate_coordinates_button.grid(row=0,column=0, pady=(0,5))

        self.save_settings_button = customtkinter.CTkButton(self.save_button_frame, corner_radius=0, text="Save Settings", command=self.saveLocationSettings)
        self.save_settings_button.grid(row=0, column=1, padx=2, pady=(0,5))

    
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

        if not (1 <= hour <= 12):
            messagebox.showerror("Error", "Hour must be between 1 and 12.", parent=self.popup)
            return

        if not (0 <= minute <= 59):
            messagebox.showerror("Error", "Minute must be between 0 and 59.", parent=self.popup)
            return
        
        if self.am_pm_menu.get() =="PM":
            if hour != 12:
                hour += 12
        else: 
            if hour == 12:
                hour =0

        date_time = datetime.datetime(
            year,
            month,
            day,
            hour,
            minute
        )
        
        timeChange = subprocess.run(["sudo", "-n", "date", "-s", str(date_time)])
        
        if timeChange.returncode != 0:
            self.log("ERROR: Could not set system date and time. Administrator permissions are required")
        else:
            self.log(f"{date_time} is set!")
            self.updateClock()

    def openTimeWindow(self):

        # a simple popup menu that will set system date and time using spinboxes and submitTime() function

        if self.popup is not None:       # checks if popup exists
            if self.popup.winfo_exists():
                return

        self.popup = customtkinter.CTkToplevel(self)
        self.popup.title("System Date and Time")
        self.popup.geometry("200x200")
        self.popup.columnconfigure(1, weight=1) #defines what columns can expand
        self.popup.columnconfigure(0, weight=1)
        self.popup.columnconfigure(2, weight=0)


        self.day_var = tkinter.StringVar(value="1")
        self.month_var = tkinter.StringVar(value="1")
        self.year_var = tkinter.StringVar(value="2026")
        self.hour_var = tkinter.StringVar(value="12")
        self.minute_var = tkinter.StringVar(value="00")

        self.day_menu_label = customtkinter.CTkLabel(self.popup, text="Day:")
        self.day_menu_label.grid(column=0, row=1, sticky="e", padx=10)
        self.day_menu = tkinter.Spinbox(self.popup, from_=1, to=31, textvariable=self.day_var, width=5)
        self.day_menu.grid(column=1, row=1, sticky="w")

        self.month_menu_label = customtkinter.CTkLabel(self.popup, text="Month:")
        self.month_menu_label.grid(column=0, row=2, sticky="e", padx=10)
        self.month_menu = tkinter.Spinbox(self.popup, from_=1, to=12, textvariable=self.month_var, width=5)
        self.month_menu.grid(column=1, row=2, sticky="w")

        self.year_menu_label = customtkinter.CTkLabel(self.popup, text="Year:")
        self.year_menu_label.grid(column=0, row=3, sticky="e", padx=10)
        self.year_menu = tkinter.Spinbox(self.popup, from_=2026, to=2080, textvariable=self.year_var, width=5)
        self.year_menu.grid(column=1, row=3, sticky="w")

        self.hour_menu_label = customtkinter.CTkLabel(self.popup, text="Hour:")
        self.hour_menu_label.grid(column=0, row=4, sticky="e", padx=10)
        self.hour_menu = tkinter.Spinbox(self.popup, from_=1, to=12, textvariable=self.hour_var, width=5)
        self.hour_menu.grid(column=1, row=4, sticky="w")

        self.am_pm_menu = customtkinter.CTkOptionMenu(self.popup, corner_radius=0, values=["AM", "PM"], width=60)
        self.am_pm_menu.grid(column=2, row=4, sticky="w")

        self.minute_menu_label = customtkinter.CTkLabel(self.popup, text="Minute:")
        self.minute_menu_label.grid(column=0, row=5, sticky="e", padx=10)
        self.minute_menu = tkinter.Spinbox(self.popup, from_=0, to=59, textvariable=self.minute_var, width=5,)
        self.minute_menu.grid(column=1, row=5, sticky="w")

        self.submit_button = customtkinter.CTkButton(self.popup, text="Set System Time", command=self.submitTime, corner_radius=0)
        self.submit_button.grid(column=0, row=6, sticky="s", columnspan=3, pady=10)

        self.popup.wait_visibility() # prevents the GUI trying to access the popup before it is fully created. 
        self.popup.focus() # brings popup in front of GUI

    def syncCoords(self, source, target, event=None):

        #function to connect lat long in the main menu to lat long in the pointing window in real time

        if isinstance(target, str):
            target = getattr(self, target, None)
        if target is not None and target.winfo_exists():
            target.delete(0, "end")
            target.insert(0, source.get())
   
    def openPointingCalculator(self):

        if self.pointing_window is not None and self.pointing_window.winfo_exists():
            self.pointing_window.deiconify()
            self.pointing_window.lift()
            return
        self.pointing_window = customtkinter.CTkToplevel(self)
        self.pointing_window.title("Pointing Calculator")
        self.pointing_window.geometry("500x610")
        self.pointing_window.protocol("WM_DELETE_WINDOW", self.pointing_window.withdraw)
    
        self.scroll = customtkinter.CTkScrollableFrame(master = self.pointing_window, width = 460, height = 260, corner_radius = 0)
        self.scroll.pack(fill = "both", expand = True, padx = 10, pady = 10)
    
        # === Row 0-1: Lat-Long ===#
        #Will automatically pull the lat and long from the main window if they're filled in

        existing_lat = self.latitude_entry.get()

        self.latitude_label = customtkinter.CTkLabel(self.scroll, text = "Observer Latitude:", justify = "left")
        self.latitude_label.grid(row = 0, column = 0, sticky = "w", padx = 10, pady = 5)
        self.pointing_latitude_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Example: 40.7128", width = 180, corner_radius = 0)
        self.pointing_latitude_entry.grid(row = 1, column = 0, sticky = "w", padx = 10, pady = 5)
        if existing_lat:                                            # only if non-blank
            self.pointing_latitude_entry.insert(0, existing_lat)


        existing_long = self.longitude_entry.get()

        self.longitude_label = customtkinter.CTkLabel(self.scroll, text = "Observer Longitude:", justify = "left")
        self.longitude_label.grid(row = 0, column = 1, sticky = "w", padx = 10, pady = 5)
        self.pointing_longitude_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Example: -74.0060", width = 180, corner_radius = 0)
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
        self.latitude_increment_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Default: 0", width = 180, corner_radius = 0)
        self.latitude_increment_entry.grid(row = 3, column = 0, sticky = "w", padx = 10, pady = 5)
    
        self.longitude_increment_label = customtkinter.CTkLabel(
            self.scroll, text="Galactic Longitude Spacing (l)\n(Degrees between points):", justify = "left")
        self.longitude_increment_label.grid(row = 2, column = 1, sticky = "w", padx = 10, pady = 5)
        self.longitude_increment_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Default: 0", width = 180, corner_radius = 0)
        self.longitude_increment_entry.grid(row = 3, column = 1, sticky = "w", padx = 10, pady = 5)
    
        # === Row 4-5 Num_points and Delay ===#
        self.num_points_label = customtkinter.CTkLabel(self.scroll, text = "Number of Data Points:", justify = "left")
        self.num_points_label.grid(row = 4, column = 0, sticky = "w", padx = 10, pady = 5)
        self.num_points_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Default: 1", width = 180, corner_radius = 0)
        self.num_points_entry.grid(row = 5, column = 0, sticky = "w", padx = 10, pady = 5)
    
        self.delay_label = customtkinter.CTkLabel(self.scroll, text = "Minutes until first point:", justify = "left")
        self.delay_label.grid(row = 4, column = 1, sticky = "w", padx = 10, pady = 5)
        self.delay_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Example: 2 for 2 minutes", width = 180, corner_radius = 0)
        self.delay_entry.grid(row = 5, column = 1, sticky = "w", padx = 10, pady = 5)

        self.delta_time_label = customtkinter.CTkLabel(self.scroll, text = "Time between datapoints:", justify = "left")
        self.delta_time_label.grid(row = 6, column = 0, sticky = "w", padx = 10, pady = 5)        
        self.delta_time_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Default: 10 for 10 minutes", width = 180, corner_radius = 0)
        self.delta_time_entry.grid(row = 7, column = 0, sticky = "w", padx = 10, pady = 5)

        self.note_label = customtkinter.CTkLabel(self.scroll, text = "Note: The starting point is \nlocated at the galactic center. \nIf you want to change this please \nlook at 'Advanced Pointing'", justify = "left")
        self.note_label.grid(row = 6, column = 1, rowspan = 2, sticky = "w", padx = 10, pady = 5)

        # === Row 6: Calculate button  ===#
        self.calculate_button = customtkinter.CTkButton(self.scroll, text="Calculate", command = self.calculate, width = 180, hover_color = "dark blue", corner_radius = 0)
        self.calculate_button.grid(row = 8, column = 0, padx = 10, pady = 5)

        self.advanced_button = customtkinter.CTkButton(self.scroll, text="Advanced Pointing", command = self.advancedPointing, width = 180, hover_color = "dark blue", corner_radius = 0)
        self.advanced_button.grid(row = 8, column = 1,  padx = 10, pady = 5)
    
        # === Box where the AzAlt text goes ===#
        self.AzAlt_box = customtkinter.CTkTextbox(self.scroll, width=450, height=220, state = "disabled", corner_radius = 0)
        self.AzAlt_box.grid(row = 9, column = 0, columnspan = 2, sticky = "w", padx = 10, pady = 5)

    def advancedPointing(self):
        if self.advanced_window is not None and self.advanced_window.winfo_exists():
            self.advanced_window.deiconify()
            self.advanced_window.lift()
            return
        # advanced setting window inside of pointing calculator

        self.advanced_window = customtkinter.CTkToplevel(self)
        self.advanced_window.title("Advanced Pointing")
        self.advanced_window.geometry("500x500")
        self.advanced_window.protocol("WM_DELETE_WINDOW", self.advanced_window.withdraw)


        self.scroll = customtkinter.CTkScrollableFrame(master = self.advanced_window, width = 460, height = 260, corner_radius = 0)
        self.scroll.pack(fill = "both", expand = True, padx = 10, pady = 10)
        
        self.Advanced_function_1_label = customtkinter.CTkLabel(self.scroll, text = "The first 'Advanced Feature' allows you to set the starting \nangle along from the galactic center.", justify = "left")
        self.Advanced_function_1_label.grid(row = 1, column = 0, columnspan = 2, sticky = "w", padx = 10, pady = 5)


        self.gal_lat_start_label = customtkinter.CTkLabel(self.scroll, text = "Starting Galactic Latitude", justify = "left")
        self.gal_lat_start_label.grid(row = 2, column = 0, sticky = "w", padx = 10, pady = 5)
        self.gal_lat_start_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Default: 0", width = 180, corner_radius = 0)
        self.gal_lat_start_entry.grid(row = 3, column = 0, sticky = "w", padx = 10, pady = 5)

        self.gal_long_start_label = customtkinter.CTkLabel(self.scroll, text = "Starting Galactic Longitude", justify = "left")
        self.gal_long_start_label.grid(row = 2, column = 1, sticky = "w", padx = 10, pady = 5)
        self.gal_long_start_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Default: 0", width = 180, corner_radius = 0)
        self.gal_long_start_entry.grid(row = 3, column = 1, sticky = "w", padx = 10, pady = 5)

        self.set_params_button = customtkinter.CTkButton(self.scroll, text="Set Parameters", command=self.setParams, width = 180, hover_color = "dark blue", corner_radius = 0)
        self.set_params_button.grid(row = 4, column = 0, padx = 10, pady = 5)


        # === Give Me Time function === #
        self.Advanced_function_2_label = customtkinter.CTkLabel(self.scroll, text = "The next 'Advanced Feature' takes in the date you want to go \nobserve, where you want to observe and the angle above the \nhorizon you want to observe and tells you when it'll be in \nthe sky ", justify = "left")
        self.Advanced_function_2_label.grid(row = 5, column = 0, columnspan = 2, sticky = "w", padx = 10, pady = 5)

        self.date_of_observation_label = customtkinter.CTkLabel(self.scroll, text = "Planned Date of Observation", justify = "left")
        self.date_of_observation_label.grid(row = 6, column = 0, sticky = "w", padx = 10, pady = 5)
        self.date_of_observation_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Example: 07-15-1943", width = 180, corner_radius = 0)
        self.date_of_observation_entry.grid(row = 7, column = 0, sticky = "w", padx = 10, pady = 5)

        self.point_height_label = customtkinter.CTkLabel(self.scroll, text = "Angle above horizon you \nwant to investigate", justify = "left")
        self.point_height_label.grid(row = 6, column = 1, sticky = "w", padx = 10, pady = 5)
        self.point_height_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Default: 10", width = 180, corner_radius = 0)
        self.point_height_entry.grid(row = 7, column = 1, sticky = "w", padx = 10, pady = 5)

        
        self.gal_lat_label = customtkinter.CTkLabel(self.scroll, text = "Galactic Latitude (b) you \nwant to investigate", justify = "left")
        self.gal_lat_label.grid(row = 8, column = 0, sticky = "w", padx = 10, pady = 5)
        self.gal_lat_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Default: 0", width = 180, corner_radius = 0)
        self.gal_lat_entry.grid(row = 9, column = 0, sticky = "w", padx = 10, pady = 5)

        self.gal_long_label = customtkinter.CTkLabel(self.scroll, text = "Galactic Longitude (l) you \nwant to investigate", justify = "left")
        self.gal_long_label.grid(row = 8, column = 1, sticky = "w", padx = 10, pady = 5)
        self.gal_long_entry = customtkinter.CTkEntry(self.scroll, placeholder_text = "Default: 0", width = 180, corner_radius = 0)
        self.gal_long_entry.grid(row = 9, column = 1, sticky = "w", padx = 10, pady = 5)

        self.gimme_time_button = customtkinter.CTkButton(self.scroll, text = "When To Observe", command = self.giveTime, width = 180, hover_color = "dark blue", corner_radius = 0)
        self.gimme_time_button.grid(row = 10, column = 0, padx = 10, pady = 5)
        
        self.altitude_plot_button = customtkinter.CTkButton(self.scroll, text = "Plot your Planned Altitude \n(default today if date empty)", command = self.altitudePlot, width = 180, hover_color = "dark blue", corner_radius = 0)
        self.altitude_plot_button.grid(row = 10, column = 1, padx = 10, pady = 5)
        
        self.Advanced_pointing_box = customtkinter.CTkTextbox(self.scroll, width=440, height=200, state = "disabled", corner_radius = 0)
        self.Advanced_pointing_box.grid(row = 11, column = 0, columnspan = 2, sticky = "w", padx = 10, pady = 5)


    def giveTime(self):

        # collects entries and gets time from azalt gimme_time function

        try:
            now = datetime.datetime.now()
            date = self.date_of_observation_entry.get().strip()
            if date:
                try:
                    month, day, year = map(int, re.split(r"\D+", date))
                    if year < 100:
                        year = year + 2000
                except ValueError:
                    raise ValueError("Planned Date of Observation is invalid.\nPlease put in form MM-DD-YYYY")
            else: year, month, day = now.year, now.month, now.day

            latitude = self.specializedErrors(self.latitude_entry, "Observer Latitude", float)
            longitude = self.specializedErrors(self.longitude_entry, "Observer Longitude", float)
            gal_lat = self.specializedErrors(self.gal_lat_entry, "Galactic Latitude you want to investigate", int, default = 0)
            gal_long = self.specializedErrors(self.gal_long_entry, "Galactic Longitude you want to investigate", int, default = 0)
            point_height = self.specializedErrors(self.point_height_entry, "Angle above the horizon you want to investigate", int, default = 10)


            self.give_time = gimme_time(latitude = latitude,
                                        longitude = longitude,
                                        gal_lat = gal_lat,
                                        gal_long = gal_long,
                                        point_height = point_height,
                                        year = year,
                                        month = month,
                                        day = day)
        
            self.Advanced_pointing_box.configure(state = "normal")
            self.Advanced_pointing_box.delete("0.0", "end")
            self.Advanced_pointing_box.insert("0.0", self.give_time)   
            self.Advanced_pointing_box.configure(state = "disabled")

        except ValueError as e:
            self.Advanced_pointing_box.configure(state = "normal")
            self.Advanced_pointing_box.delete("0.0", "end")
            self.Advanced_pointing_box.insert("0.0", f"Input error: {e}\nCheck that all fields are formatted like the examples.")
            self.Advanced_pointing_box.configure(state = "disabled")
        except Exception as e:
            self.Advanced_pointing_box.configure(state = "normal")
            self.Advanced_pointing_box.delete("0.0", "end")
            self.Advanced_pointing_box.insert("0.0", f"Calculation error: {e}")
            self.Advanced_pointing_box.configure(state = "disabled")

    def calculate(self):

        # calculations for pointing calculator

        try:
            now = datetime.datetime.now()
            adv_open = hasattr(self, "gal_long_start_entry") and self.gal_long_start_entry.winfo_exists()

            lat = self.specializedErrors(self.latitude_entry, "Observer Latitude", float)
            long = self.specializedErrors(self.longitude_entry, "Observer Longitude", float)
            delay = self.specializedErrors(self.delay_entry, "Minutes Until First Point", int, default = 1)
            num_points = self.specializedErrors(self.num_points_entry, "Number of Data Points", int, default = 1)
            lat_increment = self.specializedErrors(self.latitude_increment_entry, "Galactic Latitude Spacing", int, default = 0)
            long_increment = self.specializedErrors(self.longitude_increment_entry, "Galactic Longitude Spacing", int, default = 0)
            delta_time = self.specializedErrors(self.delta_time_entry, "Time Between Datapoints", int, default = 10)
            gal_long_start = self.specializedErrors(self.gal_long_start_entry, "Starting Galactic Longitude", int, default = 0) if adv_open else 0
            gal_lat_start = self.specializedErrors(self.gal_lat_start_entry, "Starting Galactic Latitude", int, default = 0) if adv_open else 0

            
            self.results = pointing(
                latitude = lat,
                longitude = long,
                year = now.year,
                month = now.month,
                day = now.day,
                hour = now.hour,
                minute = now.minute,
                delay = delay,
                num_points = num_points,
                lat_increment = lat_increment,
                long_increment = long_increment,
                delta_time = delta_time,
                gal_long_start = gal_long_start,
                gal_lat_start = gal_lat_start
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

    def specializedErrors(self, entry, label, cast, default = None):
        raw = entry.get().strip()
        if raw == "":
            if default is not None:
                return default
            raise ValueError(f"{label} is required")
        try:
            return cast(raw)
        except ValueError:
            kind = "a whole number" if cast is int else "a number"
            raise ValueError(f"{label} must be {kind}, got {raw}")

    def altitudePlot (self):
        try:
            now = datetime.datetime.now()

            date = self.date_of_observation_entry.get().strip()
            if date:
                try:
                    month, day, year = map(int, re.split(r"\D+", date))
                    if year < 100:
                        year += 2000
                except ValueError:
                    raise ValueError("Planned Date of Observation is invalid.\nPlease put in form MM-DD-YYYY")
            else:
                year, month, day = now.year, now.month, now.day
                
            adv_open = hasattr(self, "gal_long_start_entry") and self.gal_long_start_entry.winfo_exists()
            lat = self.specializedErrors(self.latitude_entry, "Observer latitude", float)
            long = self.specializedErrors(self.longitude_entry, "Observer longitude", float)
            gal_long = self.specializedErrors(self.gal_long_entry, "Galactic Longitude you want to investigate", int, default = 0) if adv_open else 0
            gal_lat = self.specializedErrors(self.gal_lat_entry, "Galactic Latitude you want to investigate", int, default = 0) if adv_open else 0

            times, alt, tz = altitude_plot_data(lat, long, gal_lat, gal_long, year, month, day)

            plt.figure(figsize=(4, 2))
            plt.plot(times, alt)                                       # the sky trace
            plt.axhline(0, color="gray", linestyle="--", linewidth=1)  # horizon

            if (year, month, day) == (now.year, now.month, now.day):
                now_tz = datetime.datetime.now(tz)
                i = min(range(len(times)), key = lambda k:abs((times[k] - now_tz).total_seconds()))
                plt.axvline(now_tz, color="red", linestyle=":", linewidth=1)
                plt.scatter([times[i]], [alt[i]], color="red", zorder=5)
                plt.title(f"Current Altitude: {alt[i]:.1f}°")
            else:
                j = int(alt.argmax())
                plt.scatter([times[j]], [alt[j]], color="red", zorder=5)
                plt.title(f"{month:02d}-{day:02d}-{year} — peak altitude {alt[j]:.1f}° at {times[j].strftime('%I:%M %p %Z')}")
            
            plt.xlabel("Time")
            plt.ylim(bottom = 0)
            plt.gca().yaxis.set_major_formatter('{x:.0f}°')            
            plt.tight_layout()
            plt.show()  
        except Exception as e:
            self.Advanced_pointing_box.configure(state = "normal")
            self.Advanced_pointing_box.insert("end", f"\nPlot error: {e}")
            self.Advanced_pointing_box.configure(state = "disabled")


    def setParams(self):

        # lists params from advanced pointing menu

        try:
            gal_long_start = int(self.gal_long_start_entry.get().strip() or 0)
            gal_lat_start  = int(self.gal_lat_start_entry.get().strip()  or 0)
            text = (f"Starting Galactic Latitude:  {gal_lat_start}°\n"f"Starting Galactic Longitude: {gal_long_start}°")
        except ValueError:
            text = "Starting longitude and latitude must be whole numbers."

       
        self.Advanced_pointing_box.configure(state = "normal")
        self.Advanced_pointing_box.delete("0.0", "end")
        self.Advanced_pointing_box.insert("0.0", text)   
        self.Advanced_pointing_box.configure(state = "disabled")

    
    def gpsLocator(self):

        #takes location entry and fills latitude and longitude entry
        #internet is required

        if self.testInternet():

            try:
                location = self.location_entry.get()
                if location != "":
                    lat, long = gps(location)
                    self.latitude_entry.delete(0, "end")
                    self.longitude_entry.delete(0, "end")
                    self.latitude_entry.insert(0, lat)
                    self.longitude_entry.insert(0, long)
                    #sync to pointing box
                    self.syncCoords(self.latitude_entry, "pointing_latitude_entry")
                    self.syncCoords(self.longitude_entry, "pointing_longitude_entry")
                    
                else:
                    messagebox.showerror("Location error", "Please enter a location")

            except Exception as e:
                self.log(f"Unable to find location: {e}")
        else:
            self.log("No internet connection!! Unable to find location.")
    
    def testInternet(self):
        #simple ping test to check internet

        try: 
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def gpsDisable(self):

        #disables calculate location button if no internet is found
        
        if self.testInternet():
            self.calculate_coordinates_button.configure(text="Calculate Coordinates", state="normal")
        else:
            self.calculate_coordinates_button.configure(text="Internet Required", state="disabled")
        self.after(10000, self.gpsDisable)


    def saveLocationSettings(self):

        #checks for entries before saving location entries to a txt file

        if not all([self.observer_name_entry.get().strip(), self.location_entry.get().strip(),
         self.latitude_entry.get().strip(), self.longitude_entry.get().strip() ]):

            messagebox.showerror(
                "Input Error",
                "Observer name, Location, latitude, and longitude are required.")
            return
        try:
            with open("GUI_Location_Settings.txt", "w") as file:
                file.write(self.observer_name_entry.get() + "\n")
                file.write(self.location_entry.get() + "\n")
                file.write(self.latitude_entry.get() + "\n")
                file.write(self.longitude_entry.get() + "\n")
            self.log("Settings Saved")
        except Exception as e:
            self.log(f"Error saving settings: {e}")

    def loadSettings(self):

        #loads txt settings if user saved them

        try:
            with open("GUI_Location_Settings.txt", "r") as file:
                lines = file.readlines()

                if len(lines) >= 4:
                    self.observer_name_entry.insert(0, lines[0].strip())
                    self.location_entry.insert(0, lines[1].strip())
                    self.latitude_entry.insert(0, lines[2].strip())
                    self.longitude_entry.insert(0, lines[3].strip())
                    self.log("Saved location data loaded!")

        except FileNotFoundError:
            self.log("No saved location data found")

    def updateClock(self):

        # sets the clock label on the GUI to the current system time

        now = datetime.datetime.now()

        self.clock_label.configure(
            text=now.strftime("%Y-%m-%d %H:%M:%S")
        )
        self.after(1000, self.updateClock)
    
    def updateTimeEstimate(self, event=None):

        # grabs the frequency entries and updates the estimated time displayed on the GUI

        if self.default_switch.get() =="on":
            freq_i = float(self.default_freq_i)
            freq_f = float(self.default_freq_f)
            int_time = float(self.default_int_time)
            nint = int(self.default_nint)

        else:
            try:
                freq_i = float(self.frequency_start_entry.get())
                freq_f = float(self.frequency_stop_entry.get())
                int_time = float(self.integration_time_entry.get())
                nint = int(self.integration_scans_entry.get())

            except ValueError: 
                self.estimated_time_label.configure(text="")
                return
        
        try: 
            estimated_time = ((freq_f - freq_i) * int_time * nint)
            minutes, seconds = divmod(estimated_time, 60)
            self.estimated_time_label.configure(text=f"Estimated time: {minutes:.0f}m {seconds:.0f}s")
        except Exception as e:
            self.estimated_time_label.configure(text="")
            return

    
    def enableDefaults(self):

        # removes text in entries and disables them
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
            self.updateTimeEstimate()
        else:
            self.log("Default parameters disabled")
            self.frequency_start_entry.configure(state="normal", placeholder_text="1415", fg_color=("white", "gray21"))
            self.frequency_stop_entry.configure(state="normal", placeholder_text="1425", fg_color=("white", "gray21"))
            self.integration_scans_entry.configure(state="normal", placeholder_text="10", fg_color=("white", "gray21"))
            self.integration_time_entry.configure(state="normal", placeholder_text="5", fg_color=("white", "gray21"))
            self.updateTimeEstimate()

    
    # ======================================================================
    # Sweep / Monitor mutual-exclusion control
    # ======================================================================

    def displayState(self):
        """Return the current instrument state: 'sweep', 'monitor', or 'idle'.

        Single source of truth for the indicator, the control enable/disable
        logic, and the swap behaviour.  Sweep takes priority: if a science
        thread is alive we report 'sweep' regardless of anything else.
        """
        if self.session is not None and self.session.is_alive():
            return "sweep"
        if self.monitor_worker is not None and self.monitor_worker.is_running():
            return "monitor"
        return "idle"

    def toggleSweep(self):
        """Sweep button handler.  Start Sweep always takes priority.

        - idle      → start the sweep
        - monitor   → stop the monitor (release the SDR), then start the sweep
        - sweep     → stop the sweep
        """
        state = self.displayState()
        if state == "sweep":
            self.stopCollection()
            return

        # Starting a sweep: if the monitor is up, take the device from it first.
        if state == "monitor":
            self.stopMonitor()

        self.startCollection()

    def toggleMonitor(self):
        """Monitor switch handler.

        Only reachable when no sweep is running (the switch is disabled during
        a sweep).  Turns the standalone live view on or off.
        """
        if self.monitor_switch.get() == "on":
            self.startMonitor()
        else:
            self.stopMonitor()

    def startMonitor(self):
        """Start the standalone live view at the chosen tuning frequency."""
        # Parse the tuning entry; fall back to the 21 cm line on bad input.
        try:
            freq_mhz = float(self.monitor_freq_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Frequency",
                                 "Monitor tuning must be numeric (MHz).")
            self.monitor_switch.deselect()
            return

        bias = self.monitor_lna_check.get() == "on"

        self.frames_drawn = 0
        self.display_last_freq = None
        self.monitor_worker = LiveViewWorker(
            self.spectrum_queue,
            center_freq=freq_mhz * 1e6,
            bias=bias,
        )
        try:
            self.monitor_worker.start()
        except Exception as e:
            self.log(f"Monitor failed to start: {e}")
            self.monitor_worker = None
            self.monitor_switch.deselect()
            return

        self.log(f"Monitor started at {freq_mhz:.3f} MHz"
                 f"{' with LNA power' if bias else ''}.")
        self.syncControlStates()
        self.tabview.set("Display")

    def stopMonitor(self):
        """Stop the standalone live view and release the SDR."""
        if self.monitor_worker is not None:
            self.monitor_worker.stop()
            self.monitor_worker = None
            self.log("Monitor stopped.")
        # Reflect the off state on the switch (covers the swap case, where the
        # sweep button — not the switch — triggered the stop).
        self.monitor_switch.deselect()
        self.syncControlStates()

    def monitorLnaToggled(self):
        """LNA checkbox handler — keep the Bias-T switch in sync and warn.

        The monitor's LNA power and the Configuration tab's Bias-T are the same
        physical setting, so toggling one updates the other and fires the same
        warning the Configuration switch does.
        """
        if self.monitor_lna_check.get() == "on":
            self.bias_switch.select()
        else:
            self.bias_switch.deselect()
        self.biasTwarn()

    def syncControlStates(self):
        """Enable/disable the control widgets to match the current state.

        - sweep   : monitor switch + tuning + LNA all disabled (device busy)
        - monitor : tuning + LNA disabled (can't change mid-run); switch stays
                    enabled so it can be turned off; sweep button stays enabled
                    so it can perform the swap
        - idle    : everything enabled
        """
        state = self.displayState()

        if state == "sweep":
            self.sweep_button.configure(text="Stop Sweep")
            self.monitor_switch.configure(state="disabled")
            self.monitor_freq_entry.configure(state="disabled")
            self.monitor_lna_check.configure(state="disabled")
        elif state == "monitor":
            self.sweep_button.configure(text="Start Sweep")
            self.monitor_switch.configure(state="normal")
            self.monitor_freq_entry.configure(state="disabled")
            self.monitor_lna_check.configure(state="disabled")
        else:  # idle
            self.sweep_button.configure(text="Start Sweep")
            self.monitor_switch.configure(state="normal")
            self.monitor_freq_entry.configure(state="normal")
            self.monitor_lna_check.configure(state="normal")

    def startCollection(self):

        # checks for default switch and returns either default values or text in the entry boxes
        # if default switch is off, data in the entry boxes is collected and is then checked to make sure it's valid
        # arguments are then created with values entered 
        # The cfg dictionary is made from the arguments and is then passed to the runObservation function

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
            int_time=self.int_time,
            nint=self.nint,

            biasT=self.bias_switch.get() == "on",
            data_dir=None,

            #causes a single sweep, ignore
            scan_period=None,
            total_time=None
        )

        self.startLogCapture()
        cfg = buildConfig(args, self.log)
        self.last_data_dir = cfg["data_dir"]
        self.stop_event = threading.Event()

        # Populate the Display tab's read-only summary from the entered values,
        # then start the display tap that will feed the waterfall.
        self.updateDisplaySummary()
        self.startDisplayProducer()

        self.session = threading.Thread(
            target=runObservation,
            args=(cfg, self.log, self.stop_event),
            kwargs={"on_tb_ready": self.onDisplayTbReady},
            daemon=True
        )
        self.session.start()
        time.sleep(0.2)    #wait for GNU Radio logs
        self.stopLogCapture()

        # Bring the user to the live view now that data is flowing.  Start was
        # reachable from either tab (it lives in the persistent strip), so this
        # is a convenience, not a required navigation.
        self.tabview.set("Display")
        self.syncControlStates()

        self.plotObservation()

    def stopCollection(self):

        #sends a command to stop data collection 

        if not self.session or not self.session.is_alive():
            self.log("Data collection hasn't started")
            return

        if self.stop_event:
            self.stop_event.set()

        # Stop the display tap as well; the science thread will wind down at
        # the next frequency-step boundary on its own.
        self.stopDisplayProducer()

        self.log("Stopping observation...\nWaiting for current frequency scan to finish...")

    def plotObservation(self):

        #creates plot of last observation
        #Copied and modified from abridged analysis -- untested for accuracy

        if self.session is None:
            return
        
        if self.session.is_alive():
            self.after(1000, self.plotObservation)

        else:
            # Observation finished on its own — wind down the display tap too.
            # Idempotent: harmless if stopCollection already stopped it.
            self.stopDisplayProducer()

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
        else: customtkinter.set_appearance_mode("Light")
    
    def biasTwarn(self):

        # displays a warning message if BiasT is enabled
        # !!! This function does not enable BiasT. Instead the startCollection() function passes along the value for the switch, which is then enabled when the data collection is started.

        # Keep the monitor's LNA-power checkbox in sync with this switch (they
        # are the same physical setting).  select()/deselect() are programmatic
        # and do not re-fire monitorLnaToggled, so there is no recursion.
        if hasattr(self, "monitor_lna_check"):
            if self.bias_switch.get() == "on":
                self.monitor_lna_check.select()
            else:
                self.monitor_lna_check.deselect()

        if self.bias_switch.get() == "on":
            messagebox.showwarning('WARNING', 'Only have this on if you know FOR SURE the BIAS-T is being used. \nIf you are following the CHART tutorial with the recommended LNA, it should be ON')

            self.log("Bias-T will be enabled!")
        else:
            self.log("Bias-T disabled")

    def onClose(self):

        # defines a safe shutdown procedure that closes all subprocesses before exiting the GUI

        # Release the SDR if the monitor is running.
        if self.monitor_worker is not None and self.monitor_worker.is_running():
            self.monitor_worker.stop()

        if self.jupyter_proc is not None:
            self.jupyter_proc.terminate()
        self.destroy()

    def startLogCapture(self):

        #starts a log capture on the terminal to catch commands sent from GNU radio
        #saves the previous stdout to restore logging

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
           
