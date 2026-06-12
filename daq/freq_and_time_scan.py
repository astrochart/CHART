#!/usr/bin/env python3

import argparse
import os
import time
import warnings
import datetime
import shutil

import numpy as np
import chart
import sys

def str2bool(v):
    if isinstance(v, bool):
        return v

    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True

    if v.lower() in ("no", "false", "f", "n", "0"):
        return False

    raise argparse.ArgumentTypeError("Boolean value expected.")


def collectArgs():

    ap = argparse.ArgumentParser(prog="freq_and_time_scan.py", description="CHART data collection utility", formatter_class=argparse.ArgumentDefaultsHelpFormatter)


    # long time observation settings
    ap.add_argument("--scan_period", default=0.001, type=float, help="Time between scans in hours. Low values causes a single scan")
    ap.add_argument("--total_time", default=0.001, type=float, help="Total observation time in hours. Low values causes a single scan")

    # frequency settings
    ap.add_argument("--freq_i", default=1410.0, type=float, help="Starting frequency (MHz)")
    ap.add_argument("--freq_f", default=1430.0, type=float, help="Ending frequency (MHz)")
    ap.add_argument("--df", default=1.0, type=float, help="Frequency step size (MHz)")

    # radio settings
    ap.add_argument("--veclength", default=1024, type=int, help="Number of channels for spectrum estimation")
    ap.add_argument("--samp_rate", default=2.0,type=float,help="Sample rate (MHz)")
    ap.add_argument("--int_length", default=100, type=int, help="Number of samples per integration")
    ap.add_argument("--int_time", type=float, help="Integration time in seconds. Overrides int_length.")
    ap.add_argument("--nint", default=500, type=int, help="Number of Integrations per file")
    ap.add_argument("--data_dir", default=None, type=str, help="Output directory")
    ap.add_argument("--sleep_time", default=5.0, type=float, help="Time between checks for next scan time, in seconds.")
    ap.add_argument("--biasT", default=False, type=str2bool, nargs="?", const=True, help="Enable Bias-T power")

    # metadata
    ap.add_argument("--observer", default="")
    ap.add_argument("--location", default="")
    ap.add_argument("--latitude", type=float, default=None)
    ap.add_argument("--longitude", type=float, default=None)
    ap.add_argument("--altitude", type=float, default=None)
    ap.add_argument("--azimuth", type=float, default=None)
    ap.add_argument("--description", default="")

    return ap.parse_args()

def buildConfig(args, logger=print):

    #builds a cfg dictionary from arguments
    #logging is included for CHART GUI

    if args.data_dir is None: #default for CHART GUI

        observer = args.observer.strip().replace(" ", "_")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") #current time

        data_dir = os.path.join(os.path.expanduser("~/data"), f"{observer}_{timestamp}")
        logger(f"Data directory: {data_dir}")

    else:
        data_dir = os.path.expanduser(args.data_dir)
        logger(f"Data directory: {data_dir}")

    try: 
        os.makedirs(data_dir)        #makes data directory and checks for errors 
    
    except FileExistsError:
        logger(f"Data directory already exists: {data_dir}")
        raise
    
    except OSError as e:
        logger(f"Could not create data directory: {e} \nCheck for write permissions or for illegal characters in observer name!!! ")
        raise 

    # Caclulations for integration length
    if args.int_time is not None:

        int_length = int(args.int_time * (args.samp_rate * 1e6) / args.veclength)
        actual_time = (args.veclength /(args.samp_rate * 1e6)) * int_length

        logger(f"Requested integration time: {args.int_time:.3f} s")
        logger(f"Actual integration time: {actual_time:.3f} s")

    else:
        int_length = args.int_length
        actual_time = (args.veclength / (args.samp_rate * 1e6)) * int_length

        logger(f"Integration time: {actual_time:.3f} s")

    cfg = {

        # metadata
        "observer": args.observer,
        "location": args.location,
        "latitude": args.latitude,
        "longitude": args.longitude,
        "altitude": args.altitude,
        "azimuth": args.azimuth,
        "description": args.description,

        # radio
        "freq_i": args.freq_i * 1e6,
        "freq_f": args.freq_f * 1e6,
        "df": args.df * 1e6,

        "scan_period": args.scan_period * 3600,
        "total_time": args.total_time * 3600,
        "sleep_time": args.sleep_time,

        "veclength": args.veclength,
        "samp_rate": args.samp_rate * 1e6,
        "int_length": int_length,
        "nint": args.nint,

        "bias_t": args.biasT,
        "data_dir": data_dir,
    }

    return cfg


def runObservation(cfg, logger=print, stop_event=None):

    #builds top block and runs data  collection

    if not os.path.isdir(cfg["data_dir"]): #checks that data directory exists
        raise FileNotFoundError(f"Data directory does not exist: {cfg['data_dir']}")

    try:
        tb = chart.blocks.TopBlock(
            c_freq=cfg["freq_i"],
            veclength=cfg["veclength"],
            samp_rate=cfg["samp_rate"],
            int_length=cfg["int_length"],
            nint=cfg["nint"],
            bias=cfg["bias_t"],
            data_dir=cfg["data_dir"],
            metadata=cfg,)
    
    except Exception as e:

        logger(f"SDR error: {e}\nStopping collection!!!")
        raise
    

    try:
        os.remove(tb.data_file)   #removes data file created when tb is created 
    except FileNotFoundError:
        pass

    start_time = time.time()

    while (time.time() - start_time < cfg["total_time"]): # only for long time observations
        
        if stop_event and stop_event.is_set():
            del tb
            logger("Observation Halted!!")
            return

        for freq in np.arange(      #loops through each frequency step
            cfg["freq_i"],
            cfg["freq_f"],
            cfg["df"]
        ):

            if stop_event and stop_event.is_set():
                del tb
                logger("Observation Halted!!")
                return

            logger(
                f"Frequency: {freq / 1e6:.3f} MHz"
            )

            tb.set_c_freq(freq)

            tb.blocks_head_0.reset()

            tb.set_filename()

            tb.start()
            tb.wait()

            tb.meta_save()

        time.sleep(cfg["scan_period"])      # only for long time observations
    logger("Observation Complete")
    logger("Creating zip file...")
    zip_dir = os.path.dirname(cfg["data_dir"])
    zip_file = os.path.basename(cfg["data_dir"])
    zip_path = shutil.make_archive(cfg["data_dir"], "zip", root_dir=zip_dir, base_dir=zip_file)     #creates zip
    shutil.move(zip_path, cfg["data_dir"])      #moves zip from /data to data directory 
    del tb


def main():

    args = collectArgs()

    cfg = buildConfig(args)

    runObservation(cfg)

if __name__ == "__main__":
    main()