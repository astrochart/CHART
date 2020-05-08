from . import analysis
class _MockModule:
    def __init__(self, error_message):
        self._error_message = error_message
    def __getattr__(self, attr):
        raise ImportError(self._error_message)
try:
    from . import blocks
except ImportError:
    blocks = _MockModule('GNU Radio and osmosdr is required to use '
                         'chart.blocks. See astrochart.github.io for '
                         'installation instructions.')
