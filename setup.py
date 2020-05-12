from setuptools import setup
import os
import sys
import os.path as op
import json

setup_args = {
    'name': 'chart',
    'author': 'CHART',
    'url': 'https://github.com/adampbeardsley/CHART',
    'license': 'BSD',
    'description': 'Completely Hackable Amateur Radio Telescope',
    'package_dir': {'chart': 'src/chart'},
    'packages': ['chart'],
    'include_package_data': True,
    'scripts': ['daq/freq_and_time_scan.py'],
    'version': 1.0,
    'install_requires': [
        'numpy>=1.10',
    ],
}


if __name__ == '__main__':
    setup(**setup_args)
