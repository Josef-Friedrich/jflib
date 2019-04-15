import unittest

from jflib.capturing import Capturing


class TestCapturing(unittest.TestCase):

    def test_stdout(self):
        with Capturing() as output:
            print('line 1')
            print('line 2')
        self.assertEqual(output, ['line 1', 'line 2'])
