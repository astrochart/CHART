#!/usr/bin/env python2
import chart
import time
import numpy as np
import argparse
import os
import warnings


def get_collect_args():
    """Get an argument parser for the collect script."""
    ap = argparse.ArgumentParser()
    ap.prog = "Collect.py"

    ap.add_argument('--scan_period', default=0.001, type=float, help='Time '
                    'between a scan and the next, in hours. Default is 0.001')
    ap.add_argument('--total_time', default=0.001, type=float,
                    help='Total time for all scans, in hours. Default is .001')
    ap.add_argument('--freq_i', default=1410., type=float, help='Starting frequency, '
                    'in MHz. Default is 1410.')
    ap.add_argument('--freq_f', default=1430., type=float, help='Ending frequency, '
                    'in MHz. Default is 1430.')
    ap.add_argument('--df', default=1., type=float, help='Frequency tuning step '
                    'size, in MHz. Default is 1.')
    ap.add_argument('--sleep_time', default=5., type=float, help='Sleep time '
                    'between checks for next scan time, in seconds. Default is 5.')
    ap.add_argument('--veclength', default=1024, type=int, help='Vector length '
                    '(number of channels) for spectrum estimation. Default is 1024.')
    ap.add_argument('--samp_rate', default=2., type=float, help='Sample rate '
                    'of the radio, in MHz. Default is 2.')
    ap.add_argument('--int_length', default=100, type=int, help='Number of samples '
                    'per integration. Default is 100.')
    ap.add_argument('--int_time', type=float, help='Integration time, in seconds.'
                    ' Overrides the --int_length argument.')
    ap.add_argument('--nint', default=500, type=int, help='Number of integrations '
                    'per file. Default is 500.')
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
        args.data_dir = os.getcwd()
    else:
        args.data_dir = os.path.expanduser(args.data_dir)
    if not os.path.isdir(args.data_dir):
        bad_dir = args.data_dir
        args.data_dir = os.getcwd()
        warnings.warn(bad_dir + 'Data directory not valid, using cwd = ' + args.data_dir)

    return args


def main():
    """Create a topblock and loop over frequencies and scans."""
    args = get_collect_args()
    if args.int_time is None:
        int_time = args.veclength / args.samp_rate * args.int_length
        print('int_length set to ' + str(args.int_length) + ' which corresonds'
              'to integration time of ' + str(int_time) + ' seconds.')
    else:
        args.int_length = int(args.int_time * args.samp_rate / args.vec_length)
        int_time = args.veclength / args.samp_rate * args.int_length
        print('int_time set to ' + str(args.int_time) + ' seconds. Using '
              'int_length of ' + str(args.int_length) + '. Actual integraton '
              'time is ' + str(int_time) + ' seconds.')
    tb = chart.blocks.TopBlock(c_freq=args.freq_i, veclength=args.veclength,
                               samp_rate=args.samp_rate, int_length=args.int_length,
                               nint=args.nint, data_dir=args.data_dir)
    scan_number = 0  # used as scan counter
    t0 = time.time()
    # Remove the empty file that was created when instantiating top block
    os.remove(tb.data_file)
    while time.time() - t0 < args.total_time:
        for c_freq in np.arange(args.freq_i, args.freq_f, args.df):
            print('Frequency: ' + str(c_freq / 10**6) + ' MHz')
            tb.set_c_freq(c_freq)
            tb.blocks_head_0.reset()
            tb.set_filename()
            tb.start()
            tb.wait()
            tb.meta_save()
        scan_number += 1
        while time.time() < t0 + scan_number * args.scan_period:
            time.sleep(args.sleep_time)  # Sleep before trying again
    del(tb)


if __name__ == '__main__':
    main()
