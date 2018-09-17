#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Collectrtldata
# Generated: Tue Aug 14 16:42:11 2018
##################################################

from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import fft
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.fft import window
from gnuradio.filter import firdes
from optparse import OptionParser
import chart
import osmosdr
import time
import datetime
import timeit
import numpy as np
import pprint
from ast import literal_eval


class collectrtldata(gr.top_block):

    def __init__(self, c_freq):
        gr.top_block.__init__(self, "Collectrtldata")                                   

        ##################################################
        # Variables
        ##################################################
        self.veclength = veclength = 1024
        self.samp_rate = samp_rate = 2e6
        self.int_length = 100
        self.set_filename()
        ##################################################
        # Blocks
        ##################################################
        self.rtlsdr_source_0 = osmosdr.source( args="numchan=" + str(1) + " " + "" )
        self.rtlsdr_source_0.set_sample_rate(samp_rate)
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
          
        self.fft_vxx_0 = fft.fft_vcc(veclength, True, (window.blackmanharris(1024)), True, 1)
        self.blocks_vector_to_stream_0 = blocks.vector_to_stream(gr.sizeof_float*1, 1024)
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_gr_complex*1, veclength)
        self.blocks_integrate_xx_0 = blocks.integrate_ff(self.int_length, veclength)
        self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex*1, veclength*100*100)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_float*veclength, self.data_file, False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.blocks_complex_to_mag_squared_0 = blocks.complex_to_mag_squared(veclength)
        self.chart_meta_trig_py_ff_0 =chart.meta_trig_py_ff(veclength)
        ##################################################
        # Connections
        ##################################################
        self.connect((self.chart_meta_trig_py_ff_0, 0), (self.blocks_file_sink_0, 0))    
        self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_integrate_xx_0, 0))    
        self.connect((self.blocks_head_0, 0), (self.blocks_stream_to_vector_0, 0))    
        self.connect((self.blocks_integrate_xx_0, 0), (self.chart_meta_trig_py_ff_0, 0))    
        self.connect((self.blocks_stream_to_vector_0, 0), (self.fft_vxx_0, 0))    
        self.connect((self.fft_vxx_0, 0), (self.blocks_complex_to_mag_squared_0, 0))    
        self.connect((self.rtlsdr_source_0, 0), (self.blocks_head_0, 0))    

        self.start_time = time.time()

    def get_veclength(self):
        return self.veclength

    def set_veclength(self, veclength):
        self.veclength = veclength
        self.blocks_head_0.set_length(self.veclength*100*100)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.rtlsdr_source_0.set_sample_rate(self.samp_rate)

    def set_c_freq(self, c_freq, sleep=0.5):
        """ Function to reset the tuning frequency
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

    def set_filename(self, filename=None):
        """ Function to set filename
        Args:
            filename: Optional filename. If not supplied, create filename from datetime
        """
        if filename is None:
		    self.data_file = ('/home/locorpi3b/data/' + 
                              str(datetime.datetime.now()).replace(' ', '_') + '.dat')
		    self.data_file = self.data_file.replace(':', '-')
		    self.metadata_file = self.data_file[:-3] + 'metadata.npz'
        else:
            self.data_file = filename
            self.metadata_file = filename[:-3] + 'metadata.npz'
        try:
            self.blocks_file_sink_0.open(self.data_file)
        except AttributeError:
            pass

    def parameters(self):
        d={'date': str(datetime.date.today()),
           'start_time': time.time(), 
           'samp_rate': self.samp_rate,
           'frequency': self.c_freq,
           'vector_length': self.get_veclength(),
           'int_length': self.int_length,
           #data file (.dat file it refers to)
           'data_file': self.data_file,
           #print after every integration. 100 d for each c_freq
           'metadata_file': self.metadata_file,
           'times': self.chart_meta_trig_py_ff_0.get_l()
          }
        return d

    def meta_save(self):
        np.savez(self.metadata_file,
           date = str(datetime.date.today()),
           start_time = self.start_time,
           end_time = time.time(), 
           samp_rate = self.samp_rate,
           frequency = self.c_freq,
           vector_length = self.get_veclength(),
           int_length = self.int_length,
           #data file (.dat file it refers to)
           data_file = self.data_file,
           #print after every integration. 100 d for each c_freq
           metadata_file = self.metadata_file,
           times = self.chart_meta_trig_py_ff_0.get_l())

def main(top_block_cls=collectrtldata, options=None):
    #create while loop and timer variable. while loop halts when timer variable
    #reaches certain value. tb.wait(10) added at end to create intervals of time
    dt = 30 * 60  # Time between scans, in seconds
    total_time = 24 * 60 * 60  # Total time for observation, in seconds
    i = 0
    f_i = 50 * 10**6  # Starting frequency, in Hz
    f_f = 150 * 10**6  # Ending frequency, in Hz
    df = 1 * 10**6  # tuning step size, in Hz
    tb = top_block_cls(f_i)
    t0 = time.time()
    while time.time() - t0 < total_time:
        for c_freq in range(f_i, f_f, df):
            print('Frequency: ' + str(c_freq/10**6) + ' MHz')
            tb.set_c_freq(c_freq)
            tb.blocks_head_0.reset()
            tb.set_filename()
            tb.start()
            tb.wait()
            tb.meta_save()
        i += 1
        while time.time() < t0 + i * dt:
            time.sleep(5)  # Sleep 5 seconds
    del(tb)

if __name__ == '__main__':
    main()
