import sys
import unittest

from jflib.capturing import Capturing
from jflib.termcolor import cprint


class TestCapturing(unittest.TestCase):

    def test_stdout(self):
        with Capturing() as output:
            print('line 1')
            print('line 2')
        self.assertEqual(output, ['line 1', 'line 2'])

    def test_method_tostring(self):
        with Capturing() as output:
            print('line 1')
        self.assertEqual(output.tostring(), 'line 1')

    def test_argument_stream_stdout_with_stdout(self):
        with Capturing(stream='stdout') as output:
            print('line 1')
        self.assertEqual(output, ['line 1'])

    def test_argument_stream_stdout_with_stderr(self):
        with Capturing(stream='stdout') as output:
            print('line 1', file=sys.stderr)
        self.assertEqual(output, [])

    def test_argument_stream_stderr_with_stdout(self):
        with Capturing(stream='stderr') as output:
            print('line 1')
        self.assertEqual(output, [])

    def test_argument_stream_stderr_with_stderr(self):
        with Capturing(stream='stderr') as output:
            print('line 1', file=sys.stderr)
        self.assertEqual(output, ['line 1'])

    def test_argument_clean_ansi_true(self):
        with Capturing(clean_ansi=True) as output:
            cprint('line 1', color='red')
        self.assertEqual(output, ['line 1'])

    def test_argument_clean_ansi_false(self):
        with Capturing(clean_ansi=False) as output:
            cprint('line 1', color='red')
        self.assertEqual(output, ['\x1b[31mline 1\x1b[0m'])
