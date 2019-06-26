#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Collectrtldata
# Generated: Tue Aug 14 16:42:11 2018
##################################################
#These are imports from GNU Radio 
from gnuradio import blocks 
from gnuradio import eng_notation #Engineering notation or engineering form is a version of scientific notation in which the exponent of ten must be divisible by three (i.e., they are powers of a thousand, but written as, for example, 106 instead of 10002).
from gnuradio import fft #Fourier transform function.
from gnuradio import gr #Need this to run GNU Radio.
from gnuradio.eng_option import eng_option
from gnuradio.fft import window
from gnuradio.filter import firdes 
from optparse import OptionParser #allows users to specify options in the conventional GNU/POSIX syntax, and additionally generates usage and help messages for you.
import chart 
import osmosdr #Lets you take advantage of a common software API in your application(s) independent of the underlying radio hardware.
import time #Time function
import datetime #supplies classes for manipulating dates and times in both simple and complex ways. 
import timeit #Provides a simple way to time small bits of Python code.
import numpy as np #Package for scientfic computing in python.
import pprint #Module that provides a capability to "pretty print" arbitrary Python data structures in a well formatted and more readable way. 
from ast import literal_eval # 'ast' helps Python applications to process trees of the Python abstract syntax grammar. 'literal_eval'Safely evaluate an expression node or a Unicode or Latin-1 encoded string containing a Python literal or container display. The string or node provided may only consist of the following Python literal structures: strings, numbers, tuples, lists, dicts, booleans, and None.

#this is our collect data class with an instance of gnu radio first block
class collectrtldata(gr.top_block):
#we are creating a structure to our class and only contains center frequency
    def __init__(self, c_freq):
        gr.top_block.__init__(self, "Collectrtldata")  #does this loop???                                

        ##################################################
        # Variables
        ##################################################
        self.veclength = veclength = 1024 #manually sets the vector length
        self.samp_rate = samp_rate = 2e6 #manually sets the sample rate
        self.int_length = 100 #manually sets the integration length
        self.set_filename() #names the file
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
	#these are the lines that connect each block in the visual display of GNU Radio
        self.connect((self.chart_meta_trig_py_ff_0, 0), (self.blocks_file_sink_0, 0))    
        self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_integrate_xx_0, 0))    
        self.connect((self.blocks_head_0, 0), (self.blocks_stream_to_vector_0, 0))    
        self.connect((self.blocks_integrate_xx_0, 0), (self.chart_meta_trig_py_ff_0, 0))    
        self.connect((self.blocks_stream_to_vector_0, 0), (self.fft_vxx_0, 0))    
        self.connect((self.fft_vxx_0, 0), (self.blocks_complex_to_mag_squared_0, 0))    
        self.connect((self.rtlsdr_source_0, 0), (self.blocks_head_0, 0))    

        self.start_time = time.time()
#retrieves the vector length
    def get_veclength(self):
        return self.veclength
#
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
#assigning the meta data
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
    i = 0 #used as starting value
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
