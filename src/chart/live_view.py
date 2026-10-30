#!/usr/bin/env python3
"""
live_view.py  –  LiveViewWorker and a standalone test GUI with waterfall.

Contains two things that will eventually live in separate files:

  LiveViewWorker
      Wraps a lightweight TopBlock (no science file output), starts a
      producer thread that pushes new spectra into a queue.Queue, and
      exposes start() / stop() so the main GUI can swap it out when a
      science observation begins.

  LiveViewApp
      A minimal customtkinter window used to test LiveViewWorker end-to-end.
      Has Start / Stop buttons and a matplotlib waterfall embedded via
      FigureCanvasTkAgg.  Polls the queue with self.after() — exactly the
      pattern the main ChartApp will use.

Run from the CHART repo root (with the chart venv active):
    python daq/live_view.py

What you should see:
    • A window opens with a dark waterfall panel (initially empty / navy).
    • Press Start → RTL-SDR opens, spectra begin scrolling down.
    • The status bar shows live in/out frame rates.
    • Press Stop  → producer thread and flowgraph shut down cleanly.
"""

import sys
import os
import queue
import threading
import time
import tempfile

import numpy as np
import customtkinter
import matplotlib
matplotlib.use("TkAgg")                        # must be set before pyplot import
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import chart.blocks as blocks

# runObservation lives alongside this file in daq/.  Imported here so
# ScienceWorker can run a real observation in a background thread.
from freq_and_time_scan import runObservation


# ---------------------------------------------------------------------------
# SDR / display constants — adjust to match your hardware
# ---------------------------------------------------------------------------

CENTER_FREQ      = 1420.405e6   # Hz  — hydrogen line
SAMP_RATE        = 2.0e6        # Hz
VECLENGTH        = 1024         # FFT bins
DISPLAY_INT      = 20           # FFT frames averaged per display spectrum
                                # lower = faster / noisier
                                # higher = slower / smoother
POLL_INTERVAL    = 0.05         # seconds between probe reads in producer thread

# Science branch kept minimal — live view doesn't care about recording
# but TopBlock still needs these to build the graph.
# Set NINT large enough that the flowgraph never stops on its own during
# a live view session.  At 2 MHz / 1024 bins this gives ~5 hours runtime.
_LIVE_INT_LENGTH = 50
_LIVE_NINT       = 700_000

# Waterfall display parameters
WATERFALL_ROWS   = 200          # time history rows kept on screen

# ms between queue-drain ticks (~30 Hz).  This deliberately oversamples the
# producer, which emits ~15 spectra/s.  A consumer running slower than about
# 2x the producer rate exhibits beat-frequency pauses: occasionally a tick
# finds zero new frames and the waterfall visibly stalls, recurring at the
# beat period (a few hundred ms).  Oversampling collapses any missed-frame
# gap to one tick (~33 ms), below the threshold of visible jerkiness.
GUI_POLL_MS      = 33

RESIZE_REDRAW_MS = 150          # ms between resize-background-redraw checks
                                # slower than GUI_POLL_MS so it doesn't compete
                                # with data drawing; fast enough to feel snappy
STATUS_UPDATE_S  = 1.0          # seconds between status-bar rate refreshes

# Maximum number of spectra the queue may hold.  If the consumer ever falls
# behind (e.g. an expensive blit at a large window size), the producer drops
# the oldest frame rather than letting the queue grow without bound.  At
# ~15 spectra/s a depth of 30 gives ~2 s of buffer before anything is dropped.
QUEUE_MAXDEPTH   = 30

# Frequency axis (MHz) — used for x-axis labels
FREQ_MHZ = (CENTER_FREQ / 1e6
            + np.linspace(-SAMP_RATE / 2, SAMP_RATE / 2, VECLENGTH) / 1e6)


# ---------------------------------------------------------------------------
# LiveViewWorker
# ---------------------------------------------------------------------------

class LiveViewWorker:
    """
    Manages a lightweight TopBlock for diagnostic live display.

    The worker owns a queue.Queue.  External code (the GUI) reads from it.
    The worker owns the producer thread that pushes into it.
    The GUI knows nothing about TopBlock or GNU Radio.

    Usage
    -----
        q = queue.Queue(maxsize=...)
        worker = LiveViewWorker(q)
        worker.start()          # opens SDR, begins pushing spectra
        ...
        worker.stop()           # closes SDR, producer thread exits cleanly

    Designed so the main GUI can do:
        if live_worker.is_running():
            live_worker.stop()
        science_worker.start()

    Health counters (written only by the producer thread, read by the GUI;
    int access is atomic in CPython so no lock is needed):
        frames_produced  – total spectra pushed since start()
        spectra_dropped  – spectra evicted because the queue was full
    """

    def __init__(self, spectrum_queue,
                 center_freq=CENTER_FREQ,
                 samp_rate=SAMP_RATE,
                 veclength=VECLENGTH,
                 display_int=DISPLAY_INT,
                 poll_interval=POLL_INTERVAL,
                 bias=False):

        self._queue         = spectrum_queue
        self._center_freq   = center_freq
        self._samp_rate     = samp_rate
        self._veclength     = veclength
        self._display_int   = display_int
        self._poll_interval = poll_interval
        self._bias          = bias

        self._tb            = None
        self._stop_event    = None
        self._thread        = None
        self._data_dir      = tempfile.mkdtemp(prefix="chart_live_")

        self.frames_produced = 0
        self.spectra_dropped = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self):
        """Open the SDR and begin pushing spectra into the queue."""
        if self.is_running():
            return

        self.frames_produced = 0
        self.spectra_dropped = 0
        self._stop_event = threading.Event()

        self._tb = blocks.TopBlock(
            c_freq=self._center_freq,
            veclength=self._veclength,
            samp_rate=self._samp_rate,
            int_length=_LIVE_INT_LENGTH,
            nint=_LIVE_NINT,
            bias=self._bias,
            data_dir=self._data_dir,
            display_int_length=self._display_int,
        )
        self._tb.start()

        self._thread = threading.Thread(
            target=self._producer_loop,
            daemon=True,
            name="live-view-producer",
        )
        self._thread.start()

    def stop(self):
        """Signal the producer to stop, then shut down the flowgraph."""
        if not self.is_running():
            return

        self._stop_event.set()
        self._thread.join(timeout=3.0)

        self._tb.stop()
        self._tb.wait()
        self._tb = None

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Producer loop (runs in background thread)
    # ------------------------------------------------------------------

    def _producer_loop(self):
        """Poll the GNU Radio probe; push new (c_freq, spectrum) tuples.

        Each queue item carries the current tuning so the consumer can keep
        the waterfall's frequency axis in lockstep with the data.  For the
        live view the frequency is constant, but pushing the same tuple shape
        as ScienceWorker keeps the queue contract uniform — the consumer never
        has to know which worker is upstream.

        Drop-oldest strategy: if the queue is full, evict the oldest item
        before inserting the new one.  This keeps the display showing the
        most recent data even when the consumer is briefly stalled, and
        prevents unbounded queue growth.
        """
        last_vec = None

        while not self._stop_event.is_set():
            vec = self._tb.get_display_spectrum()

            if vec is not None:
                if last_vec is None or not np.array_equal(vec, last_vec):
                    if self._queue.full():
                        try:
                            self._queue.get_nowait()
                            self.spectra_dropped += 1
                        except queue.Empty:
                            pass
                    self._queue.put_nowait((self._center_freq, vec.copy()))
                    self.frames_produced += 1
                    last_vec = vec

            time.sleep(self._poll_interval)


# ---------------------------------------------------------------------------
# ScienceWorker
# ---------------------------------------------------------------------------

class ScienceWorker:
    """
    Runs a real science observation (via runObservation) and taps its
    TopBlock's display branch to feed the same spectrum queue the live
    view uses.

    Same public interface as LiveViewWorker — start(), stop(), is_running(),
    and the frames_produced / spectra_dropped counters — so the GUI consumer
    treats both identically.  This is the payoff of the source-agnostic queue:
    the waterfall does not know or care which worker is feeding it.

    Internally, however, this is a two-thread arrangement:

      Thread A ("science"): runs runObservation(cfg, on_tb_ready=...).
          This thread spends almost all its time blocked inside the GNU Radio
          tb.wait() call for each frequency step.  We cannot poll the probe
          from here — it is frozen in C++ until each step completes.

      Thread B ("producer"): created when on_tb_ready fires, i.e. once the
          TopBlock exists.  It polls tb.get_display_spectrum() and feeds the
          queue, exactly like LiveViewWorker's producer loop.  The GNU Radio
          flowgraph runs in its own C++ threads, so the probe keeps updating
          while Thread A is blocked in wait() — Thread B reads it freely.

    Between frequency steps the flowgraph briefly stops and restarts (the
    sweep loop calls tb.start()/tb.wait() per step).  During that gap the
    probe holds its last value; the dedup check below suppresses the stale
    repeat, so the waterfall simply pauses at each retune rather than drawing
    duplicate rows.  That is the intended "watch it retune" behaviour.

    Note the cadence advantage: because the tap is *before* the science
    integration, the producer can emit several spectra per science
    integration — the live display updates faster than the recorder writes.
    """

    def __init__(self, cfg, spectrum_queue,
                 logger=print,
                 poll_interval=POLL_INTERVAL):

        self._cfg           = cfg
        self._queue         = spectrum_queue
        self._logger        = logger
        self._poll_interval = poll_interval

        self._tb              = None   # set by _on_tb_ready (in science thread)
        self._tb_ready        = threading.Event()
        self._stop_event      = None
        self._science_thread  = None
        self._producer_thread = None

        self.frames_produced = 0
        self.spectra_dropped = 0

    # ------------------------------------------------------------------
    # Public interface (mirrors LiveViewWorker)
    # ------------------------------------------------------------------

    def start(self):
        """Begin the science observation and the display tap."""
        if self.is_running():
            return

        self.frames_produced = 0
        self.spectra_dropped = 0
        self._tb       = None
        self._tb_ready.clear()
        self._stop_event = threading.Event()

        # Thread A: the science observation itself.
        self._science_thread = threading.Thread(
            target=self._science_loop,
            daemon=True,
            name="science-observation",
        )
        self._science_thread.start()

        # Thread B: the producer.  It waits for the TopBlock to exist (set by
        # _on_tb_ready, called from Thread A) before it starts polling.
        self._producer_thread = threading.Thread(
            target=self._producer_loop,
            daemon=True,
            name="science-producer",
        )
        self._producer_thread.start()

    def stop(self):
        """Signal the observation to halt and wind down both threads.

        Always releases the TopBlock (and thus the SDR device), even if the
        science thread already finished on its own.  This is what prevents the
        "Failed to set default samplerate" error on the next start — the
        device must be fully released before a new TopBlock can open it.
        """
        if self._stop_event is not None:
            # Tell runObservation's sweep loop to halt at the next step
            # boundary, and tell the producer loop to exit.
            self._stop_event.set()

        # The producer exits promptly (it only sleeps poll_interval between
        # polls).  The science thread may take longer — it has to finish the
        # current frequency step's tb.wait() before runSweep checks the
        # stop_event.  We join with generous timeouts.
        if self._producer_thread is not None:
            self._producer_thread.join(timeout=3.0)
        if self._science_thread is not None:
            self._science_thread.join(timeout=10.0)

        # Idempotent: the science thread's finally already released tb on a
        # normal exit; this catches the case where stop() is the trigger.
        self._release_tb()

    def is_running(self):
        # "Running" means the science observation is still going.  The producer
        # is subordinate to it.
        return self._science_thread is not None and self._science_thread.is_alive()

    def _release_tb(self):
        """Stop the flowgraph and drop all references to the TopBlock.

        Releasing the osmosdr source closes the USB device.  Must run before
        any subsequent start() so the RTL-SDR is free to be reopened.  Safe to
        call more than once — the second call is a no-op.
        """
        tb = self._tb
        self._tb = None
        if tb is not None:
            try:
                tb.stop()
                tb.wait()
            except Exception:
                pass
            # Brief settle so the USB device finishes releasing before a
            # possible immediate restart.
            time.sleep(0.3)

    # ------------------------------------------------------------------
    # Thread A: science observation
    # ------------------------------------------------------------------

    def _science_loop(self):
        """Run the real observation.  Blocks in tb.wait() per frequency step."""
        try:
            runObservation(
                self._cfg,
                logger=self._logger,
                stop_event=self._stop_event,
                on_tb_ready=self._on_tb_ready,
            )
        except Exception as e:
            self._logger(f"ScienceWorker: observation error: {e}")
        finally:
            # Unblock the producer if it's still waiting for a TopBlock that
            # will now never come, and signal it to stop.
            self._tb_ready.set()
            self._stop_event.set()
            # Release the SDR device here so it's freed whether the sweep
            # completed on its own or was halted.  Without this, self._tb keeps
            # the device open after a normal sweep completion, and the next
            # start() fails with "Failed to set default samplerate".
            self._release_tb()

    def _on_tb_ready(self, tb):
        """Called from Thread A once the TopBlock exists.  Hands it to B."""
        self._tb = tb
        self._tb_ready.set()

    # ------------------------------------------------------------------
    # Thread B: producer (mirrors LiveViewWorker._producer_loop)
    # ------------------------------------------------------------------

    def _producer_loop(self):
        """Wait for the TopBlock, then poll its display branch into the queue."""
        # Block until the science thread has built the TopBlock (or bailed).
        # Timeout so we don't hang forever if startup fails.
        if not self._tb_ready.wait(timeout=15.0):
            self._logger("ScienceWorker: timed out waiting for TopBlock.")
            return

        tb = self._tb
        if tb is None:
            # Observation failed before producing a TopBlock; nothing to tap.
            return

        last_vec = None

        while not self._stop_event.is_set():
            # The science sweep may delete/replace tb on us at the very end;
            # guard against it going away mid-loop.
            tb = self._tb
            if tb is None:
                break

            vec = tb.get_display_spectrum()

            if vec is not None:
                if last_vec is None or not np.array_equal(vec, last_vec):
                    if self._queue.full():
                        try:
                            self._queue.get_nowait()
                            self.spectra_dropped += 1
                        except queue.Empty:
                            pass
                    # tb.c_freq is the live tuning, updated by set_c_freq() on
                    # every sweep step — so the frequency travels with the data.
                    self._queue.put_nowait((tb.c_freq, vec.copy()))
                    self.frames_produced += 1
                    last_vec = vec

            time.sleep(self._poll_interval)


# ---------------------------------------------------------------------------
# Waterfall panel (pure matplotlib / numpy — no GNU Radio dependency)
# ---------------------------------------------------------------------------

class WaterfallPanel:
    """
    A matplotlib-based waterfall embedded in a Tk widget via FigureCanvasTkAgg.

    Accepts one numpy array at a time via push(spectrum).  Maintains a
    rolling 2-D buffer and redraws efficiently using blit.

    The panel is intentionally ignorant of the data source.

    Resize handling
    ---------------
    Blit requires a valid pixel-level background snapshot.  That snapshot
    becomes stale whenever the figure is resized.  Two design decisions keep
    this from causing jank or queue backup:

    1. The axes position is fixed with subplots_adjust() rather than
       tight_layout().  tight_layout() reflows on every canvas.draw(),
       which can move the axes bbox by a subpixel, silently breaking blit
       and forcing matplotlib into a slow full-redraw path on every push().
       Fixed margins mean the axes position is invariant — blit stays valid.

    2. canvas.draw() (the expensive full redraw needed after a resize) is
       never called from push().  Instead, _on_resize() sets a dirty flag
       and the LiveViewApp GUI loop calls redraw_background() on a slow
       separate timer (RESIZE_REDRAW_MS).  This fully decouples the
       expensive redraw from the data arrival rate.
    """

    # dB range for the colour scale — adjust to match your noise floor
    DB_LO = -5.0
    DB_HI = 25.0

    # Maximum number of frequency-axis tick labels.  matplotlib chooses "nice"
    # round values up to this count, so the labels stay readable when the
    # figure is narrow.  Lower this if ticks overlap; raise it for finer marks.
    MAX_XTICKS = 5

    def __init__(self, parent_frame, n_rows=WATERFALL_ROWS, n_cols=VECLENGTH):
        self._n_rows = n_rows
        self._n_cols = n_cols

        # Rolling buffer: row 0 = newest, row n_rows-1 = oldest
        # Initialised to DB_LO so the empty waterfall is a uniform dark colour.
        self._buf = np.full((n_rows, n_cols), self.DB_LO, dtype=np.float32)

        # --- matplotlib figure -----------------------------------------
        # Construct the Figure via the object-oriented API, NOT plt.subplots().
        # A pyplot-created figure is registered in pyplot's global registry,
        # so any later plt.show() elsewhere in the app (e.g. the post-run
        # preview plot) would also pop up THIS embedded figure in its own
        # window and could reassign its canvas — breaking blit with a
        # 'FigureCanvasBase has no get_renderer' error.  A directly-constructed
        # Figure is invisible to pyplot and owned solely by our Tk canvas.
        self._fig = Figure(figsize=(5, 4))
        self._ax = self._fig.add_subplot(111)
        self._fig.patch.set_facecolor("#1a1a2e")
        self._ax.set_facecolor("#1a1a2e")

        # imshow: (rows × cols), origin='upper' → row 0 at top (newest data)
        self._im = self._ax.imshow(
            self._buf,
            aspect="auto",
            origin="upper",
            interpolation="nearest",
            cmap="inferno",
            vmin=self.DB_LO,
            vmax=self.DB_HI,
            extent=[FREQ_MHZ[0], FREQ_MHZ[-1], n_rows, 0],
        )

        self._ax.set_xlabel("Frequency (MHz)", color="#aaaacc")
        self._ax.set_ylabel("Frames ago",      color="#aaaacc")
        self._ax.tick_params(colors="#aaaacc")
        for spine in self._ax.spines.values():
            spine.set_edgecolor("#333355")

        # Cap the number of frequency-axis ticks so labels don't overlap when
        # the figure is narrow.  MaxNLocator picks nice round values; nbins is
        # the *maximum* interval count, so the visible label count is roughly
        # MAX_XTICKS.  prune="both" drops the edge labels that tend to collide
        # with the axis frame.
        self._ax.xaxis.set_major_locator(
            MaxNLocator(nbins=self.MAX_XTICKS, prune="both")
        )

        cbar = self._fig.colorbar(self._im, ax=self._ax, pad=0.01)
        cbar.set_label("Power (dB, arb.)", color="#aaaacc")
        cbar.ax.yaxis.set_tick_params(color="#aaaacc")
        # Non-pyplot equivalent of plt.setp(...): set tick label colours directly.
        for t in cbar.ax.yaxis.get_ticklabels():
            t.set_color("#aaaacc")

        # Fixed margins instead of tight_layout().
        # tight_layout() reflows on every canvas.draw(), potentially moving
        # the axes bbox and silently breaking blit.  Fixed margins are stable
        # across resizes and leave enough room for axis labels and colorbar.
        self._fig.subplots_adjust(left=0.1, right=0.99, top=0.97, bottom=0.12)

        # --- embed in Tk -----------------------------------------------
        self._canvas = FigureCanvasTkAgg(self._fig, master=parent_frame)
        self._canvas_widget = self._canvas.get_tk_widget()
        self._canvas_widget.pack(fill="both", expand=True)

        # Initial full draw to render axes/ticks/colorbar into the canvas,
        # then capture the static background for subsequent blits.
        self._canvas.draw()
        self._bg = self._canvas.copy_from_bbox(self._fig.bbox)

        # Resize dirty flag — set by _on_resize(), cleared by
        # redraw_background().  push() never checks or clears this flag;
        # the GUI timer calls redraw_background() at RESIZE_REDRAW_MS cadence.
        self._bg_dirty = False
        self._canvas.mpl_connect("resize_event", self._on_resize)

    # ------------------------------------------------------------------

    def _on_resize(self, event):
        """Record that a resize occurred; defers the expensive redraw."""
        self._bg_dirty = True

    def set_center_freq(self, c_freq_hz):
        """Retune the frequency axis to a new center frequency.

        Updates the image extent and x-limits so the axis labels reflect the
        band currently being observed.  Marks the blit background dirty so the
        resize timer redraws the (now-changed) axis ticks; the waterfall image
        itself keeps blitting normally in between.

        Called by the consumer only when the frequency actually changes, so
        it's cheap — at most once per sweep step, not once per frame.
        """
        f_lo = (c_freq_hz - SAMP_RATE / 2) / 1e6
        f_hi = (c_freq_hz + SAMP_RATE / 2) / 1e6
        self._im.set_extent([f_lo, f_hi, self._n_rows, 0])
        self._ax.set_xlim(f_lo, f_hi)
        self._bg_dirty = True

    def redraw_background(self):
        """
        Perform a full canvas redraw and recapture the blit background.

        Called by the GUI on a slow timer (RESIZE_REDRAW_MS) when dirty.
        Never called from push() — keeping canvas.draw() off the data-arrival
        hot path is what prevents queue backup and jank after resizing.

        Returns True if a redraw was performed, False if nothing was needed.
        """
        if not self._bg_dirty:
            return False
        self._canvas.draw()
        self._bg = self._canvas.copy_from_bbox(self._fig.bbox)
        self._bg_dirty = False
        return True

    def push(self, spectrum):
        """
        Accept one new linear-power spectrum, convert to dB, update display.

        This method must stay fast — it runs in the GUI thread on every
        queue poll tick.  It does nothing except update the numpy buffer
        and issue a blit.  No canvas.draw() calls live here.

        Parameters
        ----------
        spectrum : np.ndarray, float32, shape (n_cols,)
            Linear power values from get_display_spectrum().
        """
        # Convert linear → dB, guarding against log(0)
        db = 10.0 * np.log10(np.maximum(spectrum, 1e-12))

        # Roll buffer: shift everything down one row, insert new row at top
        self._buf = np.roll(self._buf, shift=1, axis=0)
        self._buf[0, :] = db

        # Blit path — fast: update image data, restore background, draw image
        self._im.set_data(self._buf)
        self._canvas.restore_region(self._bg)
        self._ax.draw_artist(self._im)
        self._canvas.blit(self._fig.bbox)
        self._canvas.flush_events()


# ---------------------------------------------------------------------------
# Standalone test GUI
# ---------------------------------------------------------------------------

class LiveViewApp(customtkinter.CTk):
    """
    Minimal test window for LiveViewWorker + WaterfallPanel.

    Layout
    ------
    ┌─────────────────────────────────┐
    │  [Start]  [Stop]   status text  │  ← control bar
    ├─────────────────────────────────┤
    │                                 │
    │         WaterfallPanel          │  ← fills remaining space
    │                                 │
    └─────────────────────────────────┘
    """

    def __init__(self):
        super().__init__()

        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("blue")

        self.title("CHART – Live View (test)")
        self.geometry("860x540")

        # Bounded queue — producer drops oldest frame when full rather than
        # growing without bound.  See QUEUE_MAXDEPTH for rationale.
        self._spectrum_queue = queue.Queue(maxsize=QUEUE_MAXDEPTH)
        self._worker = LiveViewWorker(self._spectrum_queue)

        # Consumer-side counter, plus the reference point used to compute
        # in/out frame rates over a rolling STATUS_UPDATE_S window.
        self._frames_drawn    = 0
        self._rate_ref_time   = None   # monotonic time of last rate refresh
        self._produced_at_ref = 0      # worker.frames_produced at that time
        self._drawn_at_ref    = 0      # self._frames_drawn at that time

        # Tracks the worker's running state across ticks so the GUI can notice
        # when an observation finishes on its own (sweep complete) and reset
        # the buttons even though _on_stop was never called.
        self._worker_was_running = False

        # Current tuning, surfaced from the queue.  _last_freq is what the
        # waterfall axis is currently set to; _current_freq is shown in status.
        self._last_freq    = None
        self._current_freq = None

        # after() ids stored so _on_close can cancel both before destroying.
        self._poll_after_id   = None
        self._resize_after_id = None

        self._build_ui()

        # Data polling heartbeat — drains the spectrum queue every GUI_POLL_MS.
        self._poll_after_id = self.after(GUI_POLL_MS, self._poll_queue)

        # Resize redraw timer — checks the dirty flag every RESIZE_REDRAW_MS
        # and calls canvas.draw() only when needed.  Runs on a separate,
        # slower cadence from _poll_queue so a resize redraw never delays
        # a data update.
        self._resize_after_id = self.after(RESIZE_REDRAW_MS, self._check_resize)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.rowconfigure(0, weight=0)   # control bar — fixed height
        self.rowconfigure(1, weight=1)   # waterfall — expands
        self.columnconfigure(0, weight=1)

        # --- Control bar ---
        ctrl = customtkinter.CTkFrame(self, fg_color="transparent")
        ctrl.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")

        self._btn_start = customtkinter.CTkButton(
            ctrl, text="Start", width=100, corner_radius=0,
            command=self._on_start,
        )
        self._btn_start.grid(row=0, column=0, padx=(0, 6))

        self._btn_stop = customtkinter.CTkButton(
            ctrl, text="Stop", width=100, corner_radius=0,
            state="disabled",
            command=self._on_stop,
        )
        self._btn_stop.grid(row=0, column=1, padx=(0, 16))

        self._status = customtkinter.CTkLabel(
            ctrl, text="Idle — press Start to open SDR",
            text_color="#aaaacc",
        )
        self._status.grid(row=0, column=2, sticky="w")

        # --- Waterfall frame ---
        wf_frame = customtkinter.CTkFrame(self, corner_radius=0,
                                          fg_color="#1a1a2e")
        wf_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        self._waterfall = WaterfallPanel(wf_frame)

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------

    def _on_start(self):
        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._status.configure(text="Opening SDR…")
        self.update_idletasks()

        try:
            self._worker.start()
        except Exception as e:
            self._status.configure(text=f"ERROR: {e}")
            self._btn_start.configure(state="normal")
            self._btn_stop.configure(state="disabled")
            return

        # Reset consumer counters and the rate-measurement window
        self._frames_drawn    = 0
        self._rate_ref_time   = None
        self._produced_at_ref = 0
        self._drawn_at_ref    = 0
        self._last_freq       = None
        self._current_freq    = None
        self._worker_was_running = True
        self._status.configure(text="Running — waiting for first spectrum…")

    def _on_stop(self):
        self._btn_stop.configure(state="disabled")
        self._status.configure(text="Stopping…")
        self.update_idletasks()

        self._worker.stop()
        self._handle_worker_stopped(manual=True)

    def _handle_worker_stopped(self, manual):
        """Reset the UI after the worker stops, for either reason.

        Called from _on_stop (manual Stop press) and from _poll_queue when it
        detects the observation finished on its own.  Flushes any residual
        spectra, resets the buttons, and reports final status.
        """
        self._flush_queue()
        self._btn_start.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._worker_was_running = False

        verb = "Stopped" if manual else "Finished"
        self._status.configure(
            text=f"{verb}. {self._frames_drawn} spectra drawn."
        )

    def _flush_queue(self):
        """Discard all items currently in the spectrum queue."""
        while True:
            try:
                self._spectrum_queue.get_nowait()
            except queue.Empty:
                break

    # ------------------------------------------------------------------
    # Queue polling (GUI thread, via self.after)
    # ------------------------------------------------------------------

    def _poll_queue(self):
        """
        Drain the queue and feed each spectrum to the waterfall.

        Runs in the GUI thread via self.after(), so it can touch widgets
        directly.  Reschedules itself unconditionally so it keeps running
        whether or not the worker is active.  When the worker is stopped,
        any residual items are dropped rather than drawn.

        Each queue item is a (c_freq, spectrum) tuple.  When the tuning
        changes (a sweep step), the waterfall's frequency axis is retuned
        to match before the spectrum is drawn, so axis and data stay in sync.
        """
        worker_running = self._worker.is_running()

        # Detect the observation finishing on its own (sweep complete) so the
        # GUI resets even though _on_stop was never called.
        if self._worker_was_running and not worker_running:
            self._handle_worker_stopped(manual=False)
        self._worker_was_running = worker_running

        drained = 0
        while True:
            try:
                c_freq, spectrum = self._spectrum_queue.get_nowait()
            except queue.Empty:
                break

            if worker_running:
                if c_freq != self._last_freq:
                    self._waterfall.set_center_freq(c_freq)
                    self._last_freq    = c_freq
                    self._current_freq = c_freq
                self._waterfall.push(spectrum)
                self._frames_drawn += 1

            # Cap frames per tick so a sudden backlog (e.g. after a resize
            # stall) is worked off gradually instead of freezing the GUI
            # for one long burst.  Rarely reached: at 33 ms ticks and a
            # ~65 ms producer, most ticks see 0 or 1 frames.
            drained += 1
            if drained >= 5:
                break

        if worker_running:
            self._update_status()

        self._poll_after_id = self.after(GUI_POLL_MS, self._poll_queue)

    def _update_status(self):
        """
        Refresh the status bar with in/out frame rates and queue health.

        Recomputes at most once per STATUS_UPDATE_S so the fps figures have
        a stable measurement window and the label doesn't flicker.

          in  fps : spectra the producer pushed   (SDR → queue)
          out fps : spectra the consumer drew      (queue → waterfall)
        Healthy operation has out ≈ in.  Persistent out < in means the
        consumer is falling behind and the queue will fill (watch dropped).
        """
        now = time.monotonic()

        # First call this run — establish the reference point and wait.
        if self._rate_ref_time is None:
            self._rate_ref_time   = now
            self._produced_at_ref = self._worker.frames_produced
            self._drawn_at_ref    = self._frames_drawn
            return

        elapsed = now - self._rate_ref_time
        if elapsed < STATUS_UPDATE_S:
            return

        produced = self._worker.frames_produced
        in_fps   = (produced - self._produced_at_ref) / elapsed
        out_fps  = (self._frames_drawn - self._drawn_at_ref) / elapsed

        dropped  = self._worker.spectra_dropped
        drop_str = f"  |  dropped: {dropped}" if dropped else ""

        freq_str = (f"{self._current_freq / 1e6:.3f} MHz"
                    if self._current_freq else "—")

        self._status.configure(
            text=f"Running  —  {freq_str}"
                 f"  |  in: {in_fps:.1f} fps   out: {out_fps:.1f} fps"
                 f"  |  queued: {self._spectrum_queue.qsize()}"
                 f"  |  drawn: {self._frames_drawn}{drop_str}"
        )

        # Advance the measurement window
        self._rate_ref_time   = now
        self._produced_at_ref = produced
        self._drawn_at_ref    = self._frames_drawn

    def _check_resize(self):
        """
        Low-frequency timer: trigger a background redraw if the figure was
        resized since the last check.

        Keeping this separate from _poll_queue means an expensive canvas.draw()
        never delays a data update — the two timers are independent.
        """
        self._waterfall.redraw_background()
        self._resize_after_id = self.after(RESIZE_REDRAW_MS, self._check_resize)

    # ------------------------------------------------------------------

    def _on_close(self):
        # Cancel both pending callbacks before stopping the worker or destroying
        # the window.  Without this, Tkinter tries to fire them on a destroyed
        # widget and hangs with "invalid command name" errors.
        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
            self._resize_after_id = None

        if self._worker.is_running():
            self._worker.stop()

        # The waterfall Figure is constructed via the OO API (not pyplot), so
        # it is not in pyplot's registry and needs no plt.close().  Destroying
        # the Tk window below tears down its canvas; the Figure is then GC'd.

        self.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = LiveViewApp()
    app.mainloop()
