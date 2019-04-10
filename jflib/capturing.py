from io import StringIO
import sys
import re


class Capturing(list):
    """Capture the stdout or stdeer output. This class is designed for unit
    tests.

    :param str channel: `stdout` or `stderr`.
    :param bool clean_ansi: Clean out ANSI colors from the captured output.

    .. seealso::

        `Answer on Stackoverflow <https://stackoverflow.com/a/16571630>`_
    """

    def __init__(self, channel='stdout', clean_ansi=False):
        if channel not in ['stdout', 'stderr']:
            raise(ValueError('“channel” must be either “stdout” or “stderr”'))
        self.channel = channel
        self.clean_ansi = clean_ansi

    def __enter__(self):
        if self.channel == 'stdout':
            self._pipe = sys.stdout
            sys.stdout = self._stringio = StringIO()
        elif self.channel == 'stderr':
            self._pipe = sys.stderr
            sys.stderr = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        if self.clean_ansi:
            output = self._clean_ansi(self._stringio.getvalue())
        else:
            output = self._stringio.getvalue()
        self.extend(output.splitlines())
        del self._stringio
        if self.channel == 'stdout':
            sys.stdout = self._pipe
        elif self.channel == 'stderr':
            sys.stderr = self._pipe

    def tostring(self):
        """Convert the output into an string. By default a list of output
        lines is returned."""
        return '\n'.join(self)

    @staticmethod
    def _clean_ansi(text):
        return re.sub(r'\x1b.*?m', '', text)
