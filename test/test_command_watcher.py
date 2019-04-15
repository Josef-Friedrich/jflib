import os
import unittest

from jflib.capturing import Capturing
from jflib.command_watcher import Watch, setup_logging, WatchLoggingHandler

DIR_FILES = os.path.join(os.path.dirname(__file__), 'files')


class TestLogging(unittest.TestCase):

    def test_initialisation(self):
        handler = WatchLoggingHandler()
        logger = setup_logging(handler)
        self.assertEqual(len(logger.name), 36)

    def test_log_stdout(self):
        handler = WatchLoggingHandler()
        logger = setup_logging(handler)
        logger.stdout('stdout')
        self.assertEqual(len(handler.buffer), 1)

    def test_log_stderr(self):
        handler = WatchLoggingHandler()
        logger = setup_logging(handler)
        logger.stderr('stderr')
        self.assertEqual(len(logger.handlers[0].buffer), 1)
        self.assertEqual(logger.handlers[0].buffer[0].msg, 'stderr')
        self.assertEqual(logger.handlers[0].buffer[0].levelname, 'STDERR')


class TestCommandWatcher(unittest.TestCase):

    def test_watch_stdout(self):
        watch = Watch([os.path.join(DIR_FILES, 'stdout.sh')])
        with Capturing() as output:
            process = watch.run()
        self.assertEqual(process.returncode, 0)
        self.assertEqual(len(output), 1)
        self.assertIn('STDOUT', output[0])
        self.assertIn('One line to stdout!', output[0])

    def test_watch_stderr(self):
        watch = Watch([os.path.join(DIR_FILES, 'stderr.sh')])
        with Capturing() as output:
            process = watch.run()
        self.assertEqual(process.returncode, 1)
        self.assertEqual(len(output), 1)
        self.assertIn('STDERR', output[0])
        self.assertIn('One line to stderr!', output[0])
