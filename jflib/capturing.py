"""
Capture the stdout or stderr output.

Capture stdout:

.. code:: python

    with Capturing() as output:
        print('line 1')

is equivalent to

.. code:: python

    with Capturing(stream='stdout') as output:
        print('line 1')

Capture stderr:

.. code:: python

    with Capturing(stream='stderr') as output:
        print('line 1', file=sys.stderr)


https://capturer.readthedocs.io/en/latest/
https://github.com/bskinn/stdio-mgr
https://github.com/minrk/wurlitzer
https://pypi.org/project/OutputCatcher/0.0.9/#files
"""
import re
import sys
from io import StringIO
from typing import List, Literal, Union

Stream = Union[Literal["stdout"], Literal["stderr"]]


class Capturing(List[str]):
    """Capture the stdout or stderr output. This class is designed for unit
    tests.

    :param stream: `stdout` or `stderr`.
    :param clean_ansi: Clean out ANSI colors from the captured output.

    .. seealso::

        `Answer on Stackoverflow <https://stackoverflow.com/a/16571630>`_
    """

    def __init__(self, stream: Stream = "stdout", clean_ansi: bool = False):
        if stream not in ["stdout", "stderr"]:
            raise (ValueError("“stream” must be either “stdout” or “stderr”"))
        self.stream = stream
        self.clean_ansi = clean_ansi

    def __enter__(self):
        if self.stream == "stdout":
            self._pipe = sys.stdout
            sys.stdout = self._stringio = StringIO()
        elif self.stream == "stderr":
            self._pipe = sys.stderr
            sys.stderr = self._stringio = StringIO()
        return self

    def __exit__(self, *_):
        if self.clean_ansi:
            output = self._clean_ansi(self._stringio.getvalue())
        else:
            output = self._stringio.getvalue()
        self.extend(output.splitlines())
        del self._stringio
        if self.stream == "stdout":
            sys.stdout = self._pipe
        elif self.stream == "stderr":
            sys.stderr = self._pipe

    def tostring(self) -> str:
        """Convert the output into an string. By default a list of output
        lines is returned."""
        return "\n".join(self)

    @staticmethod
    def _clean_ansi(text: str) -> str:
        return re.sub(r"\x1b.*?m", "", text)
