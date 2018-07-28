#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Testing Print Dictionary
# Generated: Fri Jul 27 13:34:13 2018
##################################################

from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import fft
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.fft import window
from gnuradio.filter import firdes
from optparse import OptionParser
import osmosdr
import time
import tutorial
import numpy as np


class testing_print_dictionary(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Testing Print Dictionary")

        ##################################################
        # Variables
        ##################################################
        self.veclength = veclength = 1024
        self.samp_rate = samp_rate = 2e6
        self.l=[]
        ##################################################
        # Blocks
        ##################################################
        self.tutorial_mulitply_py_ff_0 = tutorial.mulitply_py_ff()
        self.rtlsdr_source_0 = osmosdr.source( args="numchan=" + str(1) + " " + "" )
        self.rtlsdr_source_0.set_sample_rate(samp_rate)
        self.rtlsdr_source_0.set_center_freq(100e6, 0)
        self.rtlsdr_source_0.set_freq_corr(0, 0)
        self.rtlsdr_source_0.set_dc_offset_mode(0, 0)
        self.rtlsdr_source_0.set_iq_balance_mode(0, 0)
        self.rtlsdr_source_0.set_gain_mode(False, 0)
        self.rtlsdr_source_0.set_gain(10, 0)
        self.rtlsdr_source_0.set_if_gain(20, 0)
        self.rtlsdr_source_0.set_bb_gain(20, 0)
        self.rtlsdr_source_0.set_antenna("", 0)
        self.rtlsdr_source_0.set_bandwidth(0, 0)
          
        self.fft_vxx_0 = fft.fft_vcc(1024, True, (window.blackmanharris(1024)), True, 1)
        self.blocks_vector_to_stream_0 = blocks.vector_to_stream(gr.sizeof_float*1, 1024)
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_gr_complex*1, veclength)
        self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_float*1)
        self.blocks_integrate_xx_0 = blocks.integrate_ff(100, veclength)
        self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex*1, 1024*100*100)
        self.blocks_complex_to_mag_squared_0 = blocks.complex_to_mag_squared(veclength)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_integrate_xx_0, 0))    
        self.connect((self.blocks_head_0, 0), (self.blocks_stream_to_vector_0, 0))    
        self.connect((self.blocks_integrate_xx_0, 0), (self.blocks_vector_to_stream_0, 0))    
        self.connect((self.blocks_stream_to_vector_0, 0), (self.fft_vxx_0, 0))    
        self.connect((self.blocks_vector_to_stream_0, 0), (self.tutorial_mulitply_py_ff_0, 0))    
        self.connect((self.fft_vxx_0, 0), (self.blocks_complex_to_mag_squared_0, 0))    
        self.connect((self.rtlsdr_source_0, 0), (self.blocks_head_0, 0))    
        self.connect((self.tutorial_mulitply_py_ff_0, 0), (self.blocks_null_sink_0, 0))    
        #self.l.append(self.tutorial_mulitply_py_ff_0.get_tdata())

    def get_veclength(self):
        return self.veclength

    def set_veclength(self, veclength):
        self.veclength = veclength

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.rtlsdr_source_0.set_sample_rate(self.samp_rate)
    
    def save_dict(self):
        np.savez("/home/locorpi3b/Documents/rtldata.metadat",metadata=self.tutorial_mulitply_py_ff_0.get_l())

def main(top_block_cls=testing_print_dictionary, options=None):

    tb = top_block_cls()
    tb.start()
    tb.wait()
    tb.save_dict()
       

if __name__ == '__main__':
    main()
