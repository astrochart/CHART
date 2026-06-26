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
    'scripts': ['daq/freq_and_time_scan.py', 'daq/chart-observe.py'],
    'version': '2.0',
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
        'scipy',
        'timezonefinder',
        'geopy'
    ],
}


if __name__ == '__main__':
    setup(**setup_args)
    venv_bin = os.path.dirname(sys.executable)
    activate_script = os.path.join(venv_bin, "activate")
    launcher = os.path.expanduser("~/Desktop/chart-observe")
    with open(launcher, 'w') as f:
        f.write(f"""#!/bin/bash
source "{activate_script}"
exec chart-observe.py
""")
    os.chmod(launcher, 0o755)
