import unittest
from jflib.command_watcher import Watch
import os

DIR_FILES = os.path.join(os.path.dirname(__file__), 'files')


class TestCommandWatcher(unittest.TestCase):

    def test_watch(self):
        watch = Watch([os.path.join(DIR_FILES, 'stdout.sh')])
        process = watch.run()
        self.assertEqual(process.returncode, 0)
