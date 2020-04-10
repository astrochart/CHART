import numpy as np
from gnuradio import gr
import time
from gnuradio import blocks as grblocks
from gnuradio import fft
from gnuradio.fft import window
import osmosdr
import datetime
import argparse
import os


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

    def __init__(self, c_freq=50e6, veclength=1024, samp_rate=2e6, int_length=100,
                 nint=100, data_dir=None):
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

        """
        gr.top_block.__init__(self, "Collectrtldata")

        ##################################################
        # Variables
        ##################################################
        self.veclength = veclength
        self.samp_rate = samp_rate
        self.int_length = int_length
        self.nint = nint
        if data_dir is None:
            self.data_dir = os.getcwd()
        else:
            self.data_dir = data_dir
        # Initialize to null to avoid empty file
        self.set_filename()
        ##################################################
        # Blocks
        ##################################################
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
        ##################################################
        # Connections
        ##################################################
        # These are the lines that connect each block in the visual display of GNU Radio
        self.connect((self.rtlsdr_source_0, 0), (self.blocks_head_0, 0))
        self.connect((self.blocks_head_0, 0), (self.blocks_stream_to_vector_0, 0))
        self.connect((self.blocks_stream_to_vector_0, 0), (self.fft_vxx_0, 0))
        self.connect((self.fft_vxx_0, 0), (self.blocks_complex_to_mag_squared_0, 0))
        self.connect((self.blocks_complex_to_mag_squared_0, 0),
                     (self.blocks_integrate_xx_0, 0))
        self.connect((self.blocks_integrate_xx_0, 0), (self.chart_meta_trig_py_ff_0, 0))
        self.connect((self.chart_meta_trig_py_ff_0, 0), (self.blocks_file_sink_0, 0))

        # Get start time
        self.start_time = time.time()

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
        self.data_file = os.path.join(self.data_dir, filebase + '.dat')
        self.metadata_file = os.path.join(self.data_dir, filebase + '.metadata.npz')
        try:
            self.blocks_file_sink_0.open(self.data_file)
        except AttributeError:
            pass

    def meta_save(self):
        """Save the metadata."""
        np.savez(self.metadata_file,
                 date=str(datetime.date.today()),
                 start_time=self.start_time,
                 end_time=time.time(),
                 samp_rate=self.samp_rate,
                 frequency=self.c_freq,
                 vector_length=self.veclength,
                 int_length=self.int_length,
                 data_file=self.data_file,
                 metadata_file=self.metadata_file,
                 times=self.chart_meta_trig_py_ff_0.get_times())
