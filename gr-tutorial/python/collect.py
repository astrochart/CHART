#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Collectrtldata
# Generated: Tue Jul 10 15:07:04 2018
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
import numpy as np
import datetime
import mulitply_py_ff as mp

class collectrtldata(gr.top_block):

    def __init__(self, c_freq):
        gr.top_block.__init__(self, "Collectrtldata")
        ##################################################
        # Variables
        ##################################################
        self.veclength = veclength = 1024
        self.samp_rate = samp_rate = 2e6
        self.c_freq = c_freq
        self.l=[]
        self.time=str(datetime.datetime.now())


        ##################################################
        # Blocks
        ##################################################
        self.tutorial_mulitply_py_ff_0 = mp.mulitply_py_ff()
        self.rtlsdr_source_0 = osmosdr.source( args="numchan=" + str(1) + " " + "" )
        self.rtlsdr_source_0.set_sample_rate(samp_rate)
        self.rtlsdr_source_0.set_center_freq(c_freq, 0)
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
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_gr_complex*1, veclength)
        self.blocks_integrate_xx_0 = blocks.integrate_ff(100, veclength)
        self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex*1, veclength*100*100)
        self.blocks_file_sink_0 = blocks.file_sink(4, "/home/locorpi3b/Documents/"+self.time+".dat", False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.blocks_complex_to_mag_squared_0 = blocks.complex_to_mag_squared(veclength)
        self.blocks_vector_to_stream_0 = blocks.vector_to_stream(4,1024)

        ##################################################
        # Connections
        ##################################################

        self.connect((self.tutorial_mulitply_py_ff_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_integrate_xx_0, 0))   
        self.connect((self.blocks_vector_to_stream_0,0),(self.tutorial_mulitply_py_ff_0,0))
        self.connect((self.blocks_head_0, 0), (self.blocks_stream_to_vector_0, 0))    
        self.connect((self.blocks_integrate_xx_0, 0), (self.blocks_vector_to_stream_0, 0))    
        self.connect((self.blocks_stream_to_vector_0, 0), (self.fft_vxx_0, 0))    
        self.connect((self.fft_vxx_0, 0), (self.blocks_complex_to_mag_squared_0, 0))    

    def get_veclength(self):
        self.connect((self.rtlsdr_source_0, 0), (self.blocks_head_0, 0))
        return self.veclength

    def set_veclength(self, veclength):
        self.veclength = veclength
        self.blocks_head_0.set_length(self.veclength*100*100)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.rtlsdr_source_0.set_sample_rate(self.samp_rate)

    '''def parameters(self):
        d={'time': time.time(), 
		   'samp_rate': self.samp_rate,
		   'frequency': self.c_freq}
		   #'data': list(np.average(
           #         self.blocks_file_sink_0.data(), 
           #         axis=-1))}
        return d'''

    def save_dict(self):
        np.savez("/home/locorpi3b/Documents/"+self.time+".metadat",record_time_start=self.time,samp_rate=self.sampe_rate,metadata=l,timeavg=list(np.average(self.blocks_file_sink0.dat,axis=0)))
        

def main(top_block_cls=collectrtldata, options=None):
    for c_freq in range(50*10**6, 52*10**6, 2*10**6):
        tb = top_block_cls(c_freq)
        tb.start()
        tb.wait()
        tb.save_dict()
        del(tb)
if __name__ == '__main__':
    main()
