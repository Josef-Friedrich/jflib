import os
import unittest

from jflib.capturing import Capturing
from jflib.command_watcher import Watch

DIR_FILES = os.path.join(os.path.dirname(__file__), 'files')


class TestCommandWatcher(unittest.TestCase):

    def test_watch_stdout(self):
        watch = Watch([os.path.join(DIR_FILES, 'stdout.sh')])
        with Capturing() as output:
            process = watch.run()
        self.assertEqual(process.returncode, 0)
        self.assertEqual(len(output), 1)
        self.assertIn('DEBUG', output[0])
        self.assertIn('One line to stdout!', output[0])

    def test_watch_stderr(self):
        watch = Watch([os.path.join(DIR_FILES, 'stderr.sh')])
        with Capturing() as output:
            process = watch.run()
        self.assertEqual(process.returncode, 1)
        self.assertEqual(len(output), 1)
        self.assertIn('ERROR', output[0])
        self.assertIn('One line to stderr!', output[0])
