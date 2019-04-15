import unittest
from jflib.command_watcher import Watch
import os

DIR_FILES = os.path.join(os.path.dirname(__file__), 'files')


class TestCommandWatcher(unittest.TestCase):

    def test_watch_stdout(self):
        watch = Watch([os.path.join(DIR_FILES, 'stdout.sh')])
        process = watch.run()
        self.assertEqual(process.returncode, 0)

    def test_watch_stderr(self):
        watch = Watch([os.path.join(DIR_FILES, 'stderr.sh')])
        process = watch.run()
        self.assertEqual(process.returncode, 1)
