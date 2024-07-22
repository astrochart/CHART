from setuptools import setup
import os
import sys
import os.path as op
import json
import shutil

setup_args = {
    'name': 'chart',
    'author': 'CHART',
    'url': 'https://github.com/adampbeardsley/CHART',
    'license': 'BSD',
    'description': 'Completely Hackable Amateur Radio Telescope',
    'package_dir': {'chart': 'src/chart'},
    'packages': ['chart'],
    'include_package_data': True,
    'scripts': ['daq/freq_and_time_scan.py', 'daq/gui.py'],
    'version': 1.0,
    'install_requires': [
        'ipython',
        'jupyter',
        'ipympl',
        'numpy>=1.20',
        'customtkinter',
        'astropy',
        'matplotlib',
        'pandas',
        'ipywidgets',
        'scipy'
    ],
}


if __name__ == '__main__':
    setup(**setup_args)
    src = shutil.which('gui.py')
    dest = os.path.expanduser('~') + '/Desktop/CHART_GUI'
    if src is not None and not os.path.exists(dest):
            os.symlink(src, dest)
