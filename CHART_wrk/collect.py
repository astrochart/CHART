#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Collectrtldata
# Generated: Tue Aug 14 16:42:11 2018
##################################################

from gnuradio import blocks 
from gnuradio import fft
from gnuradio import gr
from gnuradio.fft import window
import chart 
import osmosdr
import time
import datetime
import numpy as np
import argparse
import os


#this is our collect data class with an instance of gnu radio first block
class collectrtldata(gr.top_block):
    """Class to collect RTL data and metadata."""

    def __init__(self, c_freq=50e6, veclength=1024, samp_rate=2e6, int_length=100,
                 nint=100, data_dir=None):
        """Initialize the collect top block.
        
        Parameters
        ----------
        c_freq : float, optional
            Center frequency, in Hz. Default is 50e6.
        veclength : int, optional
            Length of FFT. Default is 100.
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
            self.data_dir = os.get_cwd()
        else:
            self.data_dir = data_dir
        self.set_filename() # names the file
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
        self.blocks_vector_to_stream_0 = blocks.vector_to_stream(gr.sizeof_float,
                                                                 self.veclength)
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_gr_complex,
                                                                 self.veclength)
        self.blocks_integrate_xx_0 = blocks.integrate_ff(self.int_length,
                                                         self.veclength)
        self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex,
                                         self.veclength * self.int_length * self.nint)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_float * veclength, 
                                                   self.data_file, False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.blocks_complex_to_mag_squared_0 = blocks.complex_to_mag_squared(self.veclength)
        self.chart_meta_trig_py_ff_0 = chart.meta_trig_py_ff(self.veclength)
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
        self.veclength = veclength
        self.blocks_head_0.set_length(self.veclength * self.int_length * self.nint)

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.rtlsdr_source_0.set_sample_rate(self.samp_rate)

    def set_c_freq(self, c_freq, sleep=0.5):
        """Function to reset the tuning frequency.

        Args:
            c_freq: center frequency, in Hz
            sleep: Time to sleep to allow the radio to settle. Default 0.5 seconds.
        """
        self.c_freq = c_freq
        self.rtlsdr_source_0.set_center_freq(c_freq, 0)
        try:
            self.chart_meta_trig_py_ff_0.l = []
        except AttributeError:
            pass
        time.sleep(sleep)

    def set_filename(self, filebase=None):
        """Function to set filename.
        
        Args:
            filebase: Optional base for filename. If not supplied,
                create filename from datetime
        """
        if filebase is None:
            filebase = str(datetime.datetime.now()).replace(' ', '_')
        self.data_file = os.path.join(self.data_dir, filebase + '.dat')
        self.metadata_file = os.path.join(self.data_dir, filebase + '.metadata.npz'
        try:
            self.blocks_file_sink_0.open(self.data_file)
        except AttributeError:
            pass

    def meta_save(self):
        np.savez(self.metadata_file,
           date = str(datetime.date.today()),
           start_time = self.start_time,
           end_time = time.time(), 
           samp_rate = self.samp_rate,
           frequency = self.c_freq,
           vector_length = self.veclength,
           int_length = self.int_length,
           data_file = self.data_file,
           metadata_file = self.metadata_file,
           times = self.chart_meta_trig_py_ff_0.get_l())

def get_collect_args():
    """Get an argument parser for the collect script."""
    
    ap = argparse.ArgumentParser()
    ap.prog = "Collect.py"
    
    ap.add_argument('--scan_period', default=0.5, type=float, help='Time '
                    'between a scan and the next, in hours. Default is 0.5.')
    ap.add_argument('--total_time', default=24., type=float,
                    help='Total time for all scans, in hours. Default is 24.')
    ap.add_argument('--freq_i', default=50., type=float, help='Starting frequency, '
                    'in MHz. Default is 50.')
    ap.add_argument('--freq_f', default=150., type=float, help='Ending frequency, '
                    'in MHz. Default is 150.')
    ap.add_argument('--df', default=1., type=float, help='Frequency tuning step '
                    'size, in MHz. Default is 1.')
    ap.add_argument('--sleep_time', default=5., type=float, help='Sleep time '
                    'between checks for next scan time, in seconds. Default is 5.')
    ap.add_argument('--veclength', default=1024, type=int, help='Vector length '
                    'for spectrum estimation. Default is 1024.')
    ap.add_argument('--samp_rate', default=1., type=float, help='Sample rate '
                    'of the radio, in MHz. Default is 1.')
    ap.add_argument('--int_length', default=100, type=int, help='Number of samples '
                    'per integration. Default is 100.')
    ap.add_argument('--nint', default=100, type=int, help='Number of integrations '
                    'per file. Default is 100.')
    ap.add_argument('--data_dir', default=None, type=str, help='Data directory. '
                    'Defaults to current working directory.')
                    
    args = ap.parse_args()
    # Convert some units for internal use
    args.scan_period *= 3600
    args.total_time *= 3600
    args.freq_i *= 1e6
    args.freq_f *= 1e6
    args.df *= 1e6
    args.samp_rate *= 1e6
    # Do a quick check on the data directory
    if args.data_dir is None:
        args.data_dir = os.get_cwd()
    if ~os.path.isdir(args.data_dir):
        args.data_dir = os.get_cwd()
        warnings.warn('Data directory not valid, using cwd = ' + args.data_dir)

    return args

def main(top_block_cls=collectrtldata):
    #create while loop and timer variable. while loop halts when timer variable
    #reaches certain value. tb.wait(10) added at end to create intervals of time
    args = get_collect_args()
    scan_number = 0 # used as scan counter
    tb = top_block_cls(cfreq=args.freq_i, veclength=args.veclength,
                       samp_rate=args.samp_rate, int_length=args.int_length,
                       nint=args.nint, data_dir=args.data_dir)
    t0 = time.time()
    while time.time() - t0 < args.total_time:
        for c_freq in range(args.freq_i, args.freq_f, args.df):
            print('Frequency: ' + str(c_freq/10**6) + ' MHz')
            tb.set_c_freq(c_freq)
            tb.blocks_head_0.reset()
            tb.set_filename()
            tb.start()
            tb.wait()
            tb.meta_save()
        i += 1
        while time.time() < t0 + scan_number * args.scan_period:
            time.sleep(args.sleep_time)  # Sleep 5 seconds
    del(tb)

if __name__ == '__main__':
    main()
