import os
import unittest

from jflib.capturing import Capturing
from jflib.command_watcher import Watch, setup_logging

DIR_FILES = os.path.join(os.path.dirname(__file__), 'files')


class TestLogging(unittest.TestCase):

    def test_initialisation(self):
        logger, handler = setup_logging()
        self.assertEqual(len(logger.name), 36)

    def test_log_stdout(self):
        logger, handler = setup_logging()
        logger.stdout('stdout')
        self.assertEqual(len(handler.buffer), 1)
        self.assertEqual(handler.buffer[0].msg, 'stdout')
        self.assertEqual(handler.buffer[0].levelname, 'STDOUT')

    def test_log_stderr(self):
        logger, handler = setup_logging()
        logger.stderr('stderr')
        self.assertEqual(len(handler.buffer), 1)
        self.assertEqual(handler.buffer[0].msg, 'stderr')
        self.assertEqual(handler.buffer[0].levelname, 'STDERR')

    def test_property_stdout(self):
        logger, handler = setup_logging()
        logger.stdout('line 1')
        logger.stdout('line 2')
        logger.stderr('stderr')
        self.assertEqual(handler.stdout, 'line 1\nline 2')

    def test_property_stderr(self):
        logger, handler = setup_logging()
        logger.stderr('line 1')
        logger.stderr('line 2')
        logger.stdout('stdout')
        self.assertEqual(handler.stderr, 'line 1\nline 2')

    def test_property_all_records(self):
        logger, handler = setup_logging()
        logger.stderr('stderr')
        logger.stdout('stdout')
        logger.error('error')
        logger.debug('debug')
        self.assertIn('stderr', handler.all_records)
        self.assertIn('stdout', handler.all_records)
        self.assertIn('error', handler.all_records)
        self.assertIn('debug', handler.all_records)


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
