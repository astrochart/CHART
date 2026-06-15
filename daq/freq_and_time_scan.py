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
    ap.add_argument("--scan_period", default=None, type=float, help="Time between scans in hours. Enables multiple scans")
    ap.add_argument("--total_time", default=None, type=float, help="Total observation time in hours. Enables multiple scans")

    # frequency settings
    ap.add_argument("--freq_i", default=1410.0, type=float, help="Starting frequency (MHz)")
    ap.add_argument("--freq_f", default=1430.0, type=float, help="Ending frequency (MHz)")
    ap.add_argument("--df", default=1.0, type=float, help="Frequency step size (MHz)")

    # radio settings
    ap.add_argument("--veclength", default=1024, type=int, help="Number of channels for spectrum estimation (FFT length)")
    ap.add_argument("--samp_rate", default=2.0,type=float,help="Sample rate (MHz)")
    ap.add_argument("--int_length", default=100, type=int, help="Number of samples per integration. Can be calulated from int_time")
    ap.add_argument("--int_time", type=float, help="Integration time in seconds. Overrides int_length.")
    ap.add_argument("--nint", default=500, type=int, help="Number of Integrations per frequency scan")
    ap.add_argument("--data_dir", default=None, type=str, help="Output directory")
    ap.add_argument("--biasT", default=False, type=str2bool, nargs="?", const=True, help="Enable Bias-T power")

    # metadata
    ap.add_argument("--observer", default="", help="Name or username of User")
    ap.add_argument("--location", default="", help="Name of location")
    ap.add_argument("--latitude", type=float, default=None, help="latitude in degrees")
    ap.add_argument("--longitude", type=float, default=None, help="longitude in degrees")
    ap.add_argument("--altitude", type=float, default=None, help="Estimated altitude of telescope")
    ap.add_argument("--azimuth", type=float, default=None, help= "Estimated azimuth of telescope")
    ap.add_argument("--description", default="", help="What are you looking at?")

    return ap.parse_args()

def buildConfig(args, logger=print):

    #builds a cfg dictionary from arguments
    #logging is included for CHART GUI

    if (args.scan_period is None) != (args.total_time is None):
        raise ValueError("scan_period and total_time must either both be specified or both omitted.")

    if args.data_dir is None: #default for CHART GUI

        observer = args.observer.strip().replace(" ", "_")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") #current time, time does not use : to prevent unwanted errors

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

    #make description.txt
    try:
        with open(data_dir + "/description.txt", "w") as file:
            file.write(args.description)
    except Exception as e:
        logger(f"Unable to create description.txt: {e}")

    # Caclulations for integration length
    if args.int_time is not None:

        int_length = int(args.int_time * (args.samp_rate * 1e6) / args.veclength)  # calulates how many FFT scans to reach integration time
        actual_time = (args.veclength /(args.samp_rate * 1e6)) * int_length        # tells user the real integration time using the calulated int_length

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
        "freq_i": args.freq_i * 1e6,                                                            # starting frequency in MHz
        "freq_f": args.freq_f * 1e6,                                                            # ending frequency in MHz
        "df": args.df * 1e6,                                                                    # Frequency step size
        "scan_period": args.scan_period * 3600 if args.scan_period is not None else None,       # wait period between serperate scans - not used by chart GUI
        "total_time": args.total_time * 3600 if args.total_time is not None else None,          # Total time for repeated scans - not used by chart GUI           
        "veclength": args.veclength,                                                            # FFT length. 1024 bins per frequency - controls resoluton
        "samp_rate": args.samp_rate * 1e6,                                                      # 2.0 ~= to +-1MHz 
        "int_length": int_length,                                                               # how many scans averaged together to reach integragtion time
        "nint": args.nint,                                                                      # number of integrations to add together
        "bias_t": args.biasT,                                                                   # enables power through LNA
        "data_dir": data_dir,                                                                   # directory for the data folder to be stored in
    }
    return cfg


def runObservation(cfg, logger=print, stop_event=None):

    def runSweep(tb):
        for freq in np.arange(cfg["freq_i"],cfg["freq_f"],cfg["df"]):           #loops through each frequency step but not the final

            if stop_event and stop_event.is_set():
                del tb
                logger("Observation Halted!!")
                return

            logger(f"Frequency: {freq / 1e6:.3f} MHz")

            tb.set_c_freq(freq)
            tb.blocks_head_0.reset()
            tb.set_filename()
            tb.start()
            tb.wait()
            tb.meta_save()

    if not os.path.isdir(cfg["data_dir"]): #checks that data directory exists
        raise FileNotFoundError(f"Data directory does not exist: {cfg['data_dir']}")

    #builds top block
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
    multi_scan = True if (cfg['scan_period'] is not None and cfg['total_time'] is not None) else False

    #runs data collection
    try:

        if (multi_scan == True)   :     
            while (time.time() - start_time < cfg["total_time"]): # only for long time observations
                
                if stop_event and stop_event.is_set():
                    del tb
                    logger("Observation Halted!!")
                    return
                runSweep(tb)
                time.sleep(cfg["scan_period"]) 
        else:
            estimated_time = ((cfg["freq_f"] - cfg["freq_i"]) / cfg["df"]) * ((cfg['veclength'] /cfg['samp_rate']) * cfg['int_length']) * cfg["nint"] #estimated time in seconds
            minutes, seconds_left = divmod(estimated_time, 60)
            logger(f"Estimated time: {minutes:.0f} Minutes and {seconds_left:.0f} Seconds")

            runSweep(tb)

        logger("Observation Complete")
        logger("Creating zip file...")
        zip_dir = os.path.dirname(cfg["data_dir"])
        zip_file = os.path.basename(cfg["data_dir"])
        zip_path = shutil.make_archive(cfg["data_dir"], "zip", root_dir=zip_dir, base_dir=zip_file)     #creates zip
        shutil.move(zip_path, cfg["data_dir"])      #moves zip from /data to data directory 
        del tb

    except Exception as e:
        logger(f"Data collection failed: {e}")
        return



def main():

    args = collectArgs()

    cfg = buildConfig(args)

    runObservation(cfg)

if __name__ == "__main__":
    main()