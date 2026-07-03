import numpy as np
import time
import datetime
import argparse
import os
import threading
from gnuradio import gr
from gnuradio import blocks as grblocks
from gnuradio import fft
from gnuradio.fft import window
import osmosdr


class meta_trig_py_ff(gr.sync_block):
    """
    Block to pass data through and record time stamps.
    """
    def __init__(self, veclength):
        self.times = []
        self.veclength = veclength
        gr.sync_block.__init__(self, name="meta_trig_py_ff",
                               in_sig=[(np.float32, self.veclength)],
                               out_sig=[(np.float32, self.veclength)])


    def work(self, input_items, output_items):
        in0 = input_items[0]
        out = output_items[0]
        # <+signal processing here+>
        out[:] = in0
        self.times.append(time.time())
        return len(output_items[0])

    def get_times(self):
        return self.times

class TopBlock(gr.top_block):
    """Class to collect RTL data and metadata."""

    # Default display integration length.  GUI can override via
    # set_display_int_length() before or after start().
    DEFAULT_DISPLAY_INT_LENGTH = 50

    def __init__(self, c_freq=50e6, veclength=1024, samp_rate=2e6, int_length=100,
                 nint=100, bias=False, data_dir=None, metadata=None,
                 display_int_length=None):

        """Initialize the collect top block.    
        Parameters
        ----------
        c_freq : float, optional
            Center frequency, in Hz. Default is 50e6.
        veclength : int, optional
            Length of FFT. Default is 1024.
        samp_rate : float, optional
            Sample rate of radio in Hz. Default is 2e6.
        int_length : int, optional
            Number of samples per integration. Default is 100.
        nint : int, optional
            Number of integrations per file. Default is 100.
        data_dir : str, optional
            Directory for data. Defaults to cwd.
        metadata : 
            additional data collected during observation passed from GUI
        display_int_length : int, optional
            Number of FFT frames averaged in the display branch.
            Independent of int_length. Defaults to DEFAULT_DISPLAY_INT_LENGTH.
            Controls update rate vs. noise floor visibility trade-off:
            lower = faster/noisier, higher = slower/smoother.
        """
        gr.top_block.__init__(self, "Collectrtldata")

        ##################################################
        # Variables
        ##################################################
        self.metadata = metadata if metadata is not None else {}
        self.veclength = veclength
        self.samp_rate = samp_rate
        self.int_length = int_length
        self.nint = nint
        self.bias = bias
        self._display_int_length = (
            display_int_length
            if display_int_length is not None
            else self.DEFAULT_DISPLAY_INT_LENGTH
        )
        if data_dir is None:
            self.data_dir = os.getcwd()
        else:
            self.data_dir = data_dir
        # Initialize to null to avoid empty file
        self.set_filename()

        ##################################################
        # Blocks
        ##################################################
        if self.bias == True:
            self.rtlsdr_source_0 = osmosdr.source(args="numchan=" + str(1) + " " + "rtl,bias=1")
        else:
            self.rtlsdr_source_0 = osmosdr.source(args="numchan=" + str(1) + " ")
        self.rtlsdr_source_0.set_sample_rate(self.samp_rate)
        self.set_c_freq(c_freq)
        self.rtlsdr_source_0.set_freq_corr(0, 0)
        self.rtlsdr_source_0.set_dc_offset_mode(0, 0)
        self.rtlsdr_source_0.set_iq_balance_mode(0, 0)
        self.rtlsdr_source_0.set_gain_mode(False, 0)
        self.rtlsdr_source_0.set_gain(45, 0)
        self.rtlsdr_source_0.set_if_gain(20, 0)
        self.rtlsdr_source_0.set_bb_gain(20, 0)
        self.rtlsdr_source_0.set_antenna("", 0)
        self.rtlsdr_source_0.set_bandwidth(0, 0)

        self.fft_vxx_0 = fft.fft_vcc(self.veclength, True,
                                     (window.blackmanharris(self.veclength)),
                                     True, 1)
        self.blocks_vector_to_stream_0 = grblocks.vector_to_stream(gr.sizeof_float,
                                                                 self.veclength)
        self.blocks_stream_to_vector_0 = grblocks.stream_to_vector(gr.sizeof_gr_complex,
                                                                 self.veclength)
        self.blocks_integrate_xx_0 = grblocks.integrate_ff(self.int_length,
                                                         self.veclength)
        self.blocks_head_0 = grblocks.head(gr.sizeof_gr_complex,
                                         self.veclength * self.int_length * self.nint)
        self.blocks_file_sink_0 = grblocks.file_sink(gr.sizeof_float * veclength,
                                                   self.data_file, False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.blocks_complex_to_mag_squared_0 = grblocks.complex_to_mag_squared(self.veclength)
        self.chart_meta_trig_py_ff_0 = meta_trig_py_ff(self.veclength)

        # ------------------------------------------------------------------
        # Display branch
        # Taps off blocks_complex_to_mag_squared_0 — upstream of the science
        # integration — so display settings are independent of science settings.
        #
        # blocks_complex_to_mag_squared_0
        #         |                    |
        #  (science branch)     (display branch)
        # blocks_integrate_xx_0   blocks_integrate_xx_display
        #         |                    |
        #   meta_trig_py_ff_0   blocks_probe_signal_vf_0
        #         |
        #   blocks_file_sink_0
        # ------------------------------------------------------------------
        self.blocks_integrate_xx_display = grblocks.integrate_ff(
            self._display_int_length, self.veclength
        )
        self.blocks_probe_signal_vf_0 = grblocks.probe_signal_vf(self.veclength)

        ##################################################
        # Connections
        ##################################################
        # These are the lines that connect each block in the visual display of GNU Radio
        self.connect((self.rtlsdr_source_0, 0), (self.blocks_head_0, 0))
        self.connect((self.blocks_head_0, 0), (self.blocks_stream_to_vector_0, 0))
        self.connect((self.blocks_stream_to_vector_0, 0), (self.fft_vxx_0, 0))
        self.connect((self.fft_vxx_0, 0), (self.blocks_complex_to_mag_squared_0, 0))

        # Science branch (unchanged)
        self.connect((self.blocks_complex_to_mag_squared_0, 0),
                     (self.blocks_integrate_xx_0, 0))
        self.connect((self.blocks_integrate_xx_0, 0), (self.chart_meta_trig_py_ff_0, 0))
        self.connect((self.chart_meta_trig_py_ff_0, 0), (self.blocks_file_sink_0, 0))

        # Display branch (fan-out from complex_to_mag_squared)
        self.connect((self.blocks_complex_to_mag_squared_0, 0),
                     (self.blocks_integrate_xx_display, 0))
        self.connect((self.blocks_integrate_xx_display, 0),
                     (self.blocks_probe_signal_vf_0, 0))

        # Get start time
        self.start_time = time.time()

    # ------------------------------------------------------------------
    # Display branch public API
    # ------------------------------------------------------------------

    def get_display_spectrum(self):
        """Return the most recent display-averaged power spectrum.

        Returns a numpy float32 array of length veclength containing linear
        power values (arbitrary units, not yet converted to dB).  The array
        is a copy — safe to hold onto after the flowgraph updates.

        Returns None if the flowgraph has not produced a vector yet (i.e.
        fewer than display_int_length FFT frames have been processed since
        the last start() call).
        """
        vec = self.blocks_probe_signal_vf_0.level()
        if vec is None:
            return None
        arr = np.array(vec, dtype=np.float32)
        # probe_signal_vf initialises its internal buffer to all-zeros.
        # An all-zero vector means no data has arrived yet.
        if not np.any(arr):
            return None
        return arr

    def set_display_int_length(self, n):
        """Change the display averaging depth while the flowgraph is running.

        Parameters
        ----------
        n : int
            Number of FFT frames to average.  Must be >= 1.
            Lower values give faster updates with more noise.
            Higher values give slower updates with a smoother spectrum.

        Note: GNU Radio's integrate_ff does not support runtime changes to
        integration length, so this method stops the flowgraph, rebuilds the
        display branch blocks with the new length, reconnects, and restarts.
        Only call this when the flowgraph is running — it handles start/stop
        internally.  The science branch and file sink are unaffected.
        """
        n = max(1, int(n))
        if n == self._display_int_length:
            return

        was_running = self.is_running() if hasattr(self, 'is_running') else False

        # GNU Radio top_block doesn't expose is_running() before GR 3.9.
        # Safest to just stop unconditionally and swallow the error.
        try:
            self.stop()
            self.wait()
        except Exception:
            pass

        # Disconnect old display branch
        try:
            self.disconnect((self.blocks_complex_to_mag_squared_0, 0),
                            (self.blocks_integrate_xx_display, 0))
            self.disconnect((self.blocks_integrate_xx_display, 0),
                            (self.blocks_probe_signal_vf_0, 0))
        except Exception:
            pass

        # Rebuild with new integration length
        self._display_int_length = n
        self.blocks_integrate_xx_display = grblocks.integrate_ff(n, self.veclength)

        self.connect((self.blocks_complex_to_mag_squared_0, 0),
                     (self.blocks_integrate_xx_display, 0))
        self.connect((self.blocks_integrate_xx_display, 0),
                     (self.blocks_probe_signal_vf_0, 0))

        if was_running:
            self.start()

    @property
    def display_int_length(self):
        return self._display_int_length

    # ------------------------------------------------------------------
    # Existing methods (unchanged)
    # ------------------------------------------------------------------

    def set_veclength(self, veclength):
        """Set vector length."""
        self.veclength = veclength
        self.blocks_head_0.set_length(self.veclength * self.int_length * self.nint)

    def set_samp_rate(self, samp_rate):
        """Set sample rate."""
        self.samp_rate = samp_rate
        self.rtlsdr_source_0.set_sample_rate(self.samp_rate)

    def set_c_freq(self, c_freq, sleep=0.5):
        """Set the tuning frequency.

        Args:
            c_freq: center frequency, in Hz
            sleep: Time to sleep to allow the radio to settle. Default 0.5 seconds.
        """
        self.c_freq = c_freq
        self.rtlsdr_source_0.set_center_freq(c_freq, 0)
        try:
            self.chart_meta_trig_py_ff_0.times = []
        except AttributeError:
            pass
        time.sleep(sleep)

    def set_filename(self, filebase=None):
        """Set filename.

        Args:
            filebase: Optional base for filename. If not supplied,
                create filename from datetime
        """
        if filebase is None:
            filebase = str(datetime.datetime.now()).replace(' ', '_')
            filebase = filebase.replace(':', '-')
        self.data_file = os.path.join(self.data_dir, filebase + '.dat')
        self.metadata_file = os.path.join(self.data_dir, filebase + '.metadata.npz')
        try:
            self.blocks_file_sink_0.open(self.data_file)
        except AttributeError:
            pass

    def meta_save(self):
        """Save the metadata."""
        np.savez(self.metadata_file,
                 date=datetime.date.today(),
                 start_time=self.start_time,
                 end_time=time.time(),
                 samp_rate=self.samp_rate,
                 frequency=self.c_freq,
                 vector_length=self.veclength,
                 int_length=self.int_length,
                 data_file=self.data_file,
                 metadata_file=self.metadata_file,
                 times=self.chart_meta_trig_py_ff_0.get_times(),
                 dtype=[np.float32],
                 observer=self.metadata.get("observer", ""),
                 location=self.metadata.get("location", ""),
                 altitude=self.metadata.get("altitude", None),
                 azimuth=self.metadata.get("azimuth", None),
                 description=self.metadata.get("description", ""),
                 latitude=self.metadata.get("latitude", None),
                 longitude=self.metadata.get("longitude", None),
                )
