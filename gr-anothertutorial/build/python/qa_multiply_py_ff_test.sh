#!/bin/sh
export VOLK_GENERIC=1
export GR_DONT_LOAD_PREFS=1
export srcdir=/home/locorpi3b/block_writing/gr-anothertutorial/python
export GR_CONF_CONTROLPORT_ON=False
export PATH=/home/locorpi3b/block_writing/gr-anothertutorial/build/python:$PATH
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH
export PYTHONPATH=/home/locorpi3b/block_writing/gr-anothertutorial/build/swig:$PYTHONPATH
/usr/bin/python2 /home/locorpi3b/block_writing/gr-anothertutorial/python/qa_multiply_py_ff.py 
