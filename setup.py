from setuptools import setup
import os
import sys
import os.path as op
import json
import shutil
from setuptools.command.install import install as _install


setup_args = {
    'name': 'chart',
    'author': 'CHART',
    'url': 'https://github.com/astrochart/CHART',
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


class CHART_Install(_install):
    user_options = _install.user_options + [
        ('analysis', None, 'install analysis mode without daq scripts or desktop launcher'),
    ]
    boolean_options = _install.boolean_options + ['analysis']

    def initialize_options(self):
        super().initialize_options()
        self.analysis = False

    def finalize_options(self):
        super().finalize_options()
        if self.analysis or os.getenv('CHART_ANALYSIS', '0') == '1':
            self.distribution.scripts = []

    def run(self):
        super().run()
        if self.analysis or os.getenv('CHART_ANALYSIS', '0') == '1':
            return
        self._create_desktop_launcher()

    def _create_desktop_launcher(self):
        venv_bin = os.path.dirname(sys.executable)
        activate_script = os.path.join(venv_bin, 'activate')
        launcher = os.path.expanduser('~/Desktop/chart-observe')
        with open(launcher, 'w') as f:
            f.write(f"""#!/bin/bash
source \"{activate_script}\"
exec chart-observe.py
""")
        os.chmod(launcher, 0o755)

setup_args['cmdclass'] = {'install': CHART_Install}

if __name__ == '__main__':
    setup(**setup_args)
