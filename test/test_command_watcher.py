import os
import unittest
from unittest import mock

from jflib.capturing import Capturing
from jflib.command_watcher import Watch, setup_logging, CommandWatcherError
from jflib.config_reader import ConfigReader

DIR_FILES = os.path.join(os.path.dirname(__file__), 'files')
INI_FILE = os.path.join(DIR_FILES, 'email.ini')


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


class TestColorizedPrint(unittest.TestCase):

    def setUp(self):
        self.logger, _ = setup_logging()

    def test_critical(self):
        with Capturing(stream='stderr') as output:
            self.logger.critical('CRITICAL 50')
        self.assertEqual(
            output[0][20:],
            '\x1b[1m\x1b[7m\x1b[31m CRITICAL '
            '\x1b[0m \x1b[1m\x1b[31mCRITICAL 50\x1b[0m'
        )

    def test_error(self):
        with Capturing(stream='stderr') as output:
            self.logger.error('ERROR 40')
        self.assertEqual(
            output[0][20:],
            '\x1b[7m\x1b[31m ERROR    \x1b[0m \x1b[31mERROR 40\x1b[0m'
        )

    def test_stderr(self):
        with Capturing(stream='stderr') as output:
            self.logger.stderr('STDERR 35')
        self.assertEqual(
            output[0][20:],
            '\x1b[2m\x1b[7m\x1b[31m STDERR   '
            '\x1b[0m \x1b[2m\x1b[31mSTDERR 35\x1b[0m'
        )

    def test_warning(self):
        with Capturing() as output:
            self.logger.warning('WARNING 30')
        self.assertEqual(
            output[0][20:],
            '\x1b[7m\x1b[33m WARNING  \x1b[0m \x1b[33mWARNING 30\x1b[0m'
        )

    def test_info(self):
        with Capturing() as output:
            self.logger.info('INFO 20')
        self.assertEqual(
            output[0][20:],
            '\x1b[7m\x1b[32m INFO     \x1b[0m \x1b[32mINFO 20\x1b[0m'
        )

    def test_debug(self):
        with Capturing() as output:
            self.logger.debug('DEBUG 10')
        self.assertEqual(
            output[0][20:],
            '\x1b[7m\x1b[37m DEBUG    \x1b[0m \x1b[37mDEBUG 10\x1b[0m'
        )

    def test_stdout(self):
        with Capturing() as output:
            self.logger.stdout('STDOUT 5')
        self.assertEqual(
            output[0][20:],
            '\x1b[2m\x1b[7m\x1b[37m STDOUT   \x1b[0m '
            '\x1b[2m\x1b[37mSTDOUT 5\x1b[0m'
        )

    def test_noset(self):
        with Capturing() as output:
            self.logger.log(1, 'NOTSET 0')
        self.assertEqual(
            output[0][20:],
            '\x1b[7m\x1b[30m Level 1  \x1b[0m \x1b[30mNOTSET 0\x1b[0m'
        )


class TestClassWatch(unittest.TestCase):

    def setUp(self):
        self.cmd_stderr = os.path.join(DIR_FILES, 'stderr.sh')
        self.cmd_stdout = os.path.join(DIR_FILES, 'stdout.sh')

    def test_argument_config_file(self):
        watch = Watch(config_file=INI_FILE)
        self.assertEqual(watch._config_reader.email.to_addr, 'to@example.com')

    def test_watch_stdout(self):
        watch = Watch()
        with Capturing() as output:
            process = watch.run(self.cmd_stdout)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(len(output), 3)
        self.assertIn('STDOUT', output[1])
        self.assertIn('One line to stdout!', output[1])
        self.assertIn('Execution time: ', output[2])

    def test_watch_stderr(self):
        watch = Watch(raise_exceptions=False)
        with Capturing(stream='stderr') as output:
            process = watch.run(self.cmd_stderr)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(len(output), 1)
        self.assertIn('STDERR', output[0])
        self.assertIn('One line to stderr!', output[0])

    def test_watch_run_multiple(self):
        watch = Watch(raise_exceptions=False)
        watch.run(self.cmd_stdout)
        watch.run(self.cmd_stderr)
        self.assertEqual(len(watch._log_handler.buffer), 6)

    def test_method_run_kwargs(self):
        watch = Watch()
        with mock.patch('subprocess.Popen') as Popen:
            process = Popen.return_value
            process.stdout = b''
            process.stderr = b''
            process.returncode = 0
            watch.run('ls', cwd='/')
        Popen.assert_called_with(['ls'], bufsize=1, cwd='/', stderr=-1,
                                 stdout=-1)

    def test_method_run_kwargs_exception(self):
        watch = Watch()
        with self.assertRaises(TypeError):
            watch.run('ls', xxx=False)

    def test_property_stdout(self):
        watch = Watch()
        watch.log.stdout('stdout')
        self.assertEqual(watch.stdout, 'stdout')

    def test_property_stderr(self):
        watch = Watch()
        watch.log.stderr('stderr')
        self.assertEqual(watch.stderr, 'stderr')

    def test_property_completed_processes(self):
        watch = Watch()
        self.assertEqual(watch._completed_processes, [])
        watch.run(['ls'])
        watch.run(['ls', '-l'])
        watch.run(['ls', '-la'])
        self.assertEqual(len(watch._completed_processes), 3)

    def test_method_send_email(self):
        watch = Watch()
        watch.log.info('info')
        watch.log.error('error')
        watch.log.debug('debug')

        with mock.patch('smtplib.SMTP') as SMTP:
            watch.send_email(
                from_addr='from@example.com',
                to_addr='to@example.com',
                subject='Subject',
                smtp_login='Login',
                smtp_password='Password',
                smtp_server='smtp.example.com:587'
            )

        SMTP.assert_called_with('smtp.example.com:587')
        server = SMTP.return_value
        server.login.assert_called_with('Login', 'Password')
        call_args = server.sendmail.call_args[0]
        self.assertEqual(call_args[0], 'from@example.com')
        self.assertEqual(call_args[1], ['to@example.com'])
        self.assertIn(
            'From: from@example.com\nTo: to@example.com\n',
            call_args[2]
        )

    def test_method_send_email_with_config_reader(self):
        config_reader = ConfigReader(ini=INI_FILE)
        watch = Watch(config_reader=config_reader)
        watch.log.info('info')

        with mock.patch('smtplib.SMTP') as SMTP:
            watch.send_email(
                subject='Subject',
            )

        SMTP.assert_called_with('smtp.example.com:587')
        server = SMTP.return_value
        server.login.assert_called_with('Login', 'Password')
        call_args = server.sendmail.call_args[0]
        self.assertEqual(call_args[0], 'from@example.com')
        self.assertEqual(call_args[1], ['to@example.com'])
        self.assertIn(
            'From: from@example.com\nTo: to@example.com\n',
            call_args[2]
        )

    def test_method_send_email_subject(self):
        config_reader = ConfigReader(ini=INI_FILE)
        watch = Watch(config_reader=config_reader)
        send_email = mock.Mock()
        watch._log_handler.send_email = send_email
        watch.run('ls')
        watch.run(['ls', '-l'])

        watch.send_email()
        send_email.assert_called_with(
            from_addr='from@example.com',
            smtp_login='Login',
            smtp_password='Password',
            smtp_server='smtp.example.com:587',
            subject='command_watcher: ls; ls -l',
            to_addr='to@example.com'
        )

    def test_exception(self):
        watch = Watch()
        with self.assertRaises(CommandWatcherError):
            watch.run(self.cmd_stderr)
