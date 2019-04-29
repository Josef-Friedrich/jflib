import os
import unittest
from unittest import mock

from jflib.capturing import Capturing
from jflib.command_watcher import \
    CommandWatcherError, \
    EmailMessage, \
    EmailSender, \
    NscaMessage, \
    NscaSender, \
    setup_logging, \
    Watch, \
    HOSTNAME, \
    USERNAME

DIR_FILES = os.path.join(os.path.dirname(__file__), 'files')
CONF = os.path.join(DIR_FILES, 'command_watcher', 'conf.ini')
FROM_ADDR = '{0} <{1}@{0}>'.format(HOSTNAME, USERNAME)


class TestLogging(unittest.TestCase):

    def test_initialisation(self):
        logger, _ = setup_logging()
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


class TestClassEmailMessageBuildSubject(unittest.TestCase):

    def build_subject(self, service_name, subject_prefix='',
                      completed_processes=[]):
        mocked_processes = []
        for args in completed_processes:
            mocked_processes.append(mock.Mock(args=args))
        return EmailMessage._build_subject(service_name, subject_prefix,
                                           mocked_processes)

    def test_all_args(self):
        result = self.build_subject('service', '#CW', (['ls'], ['ls', '-l']))
        self.assertEqual(result, '#CW: service (ls; ls -l)')

    def test_without_completed_processes(self):
        result = self.build_subject('service', '#CW')
        self.assertEqual(result, '#CW: service')

    def test_only_service(self):
        result = self.build_subject('service')
        self.assertEqual(result, 'service')


class TestClassEmailMessage(unittest.TestCase):

    def setUp(self):
        self.message = EmailMessage('to@example.com', 'service', 'body', '#Cw')

    def test_property_to_addr(self):
        self.assertEqual(self.message.to_addr, 'to@example.com')

    def test_property_subject(self):
        self.assertEqual(self.message.subject, '#Cw: service')

    def test_property_body(self):
        self.assertEqual(self.message.body, 'body')

    def test_magic_method_str(self):
        self.assertEqual(
            str(self.message),
            '[Email Message] To address: to@example.com, Subject: #Cw: service'
        )


class TestClassEmailSender(unittest.TestCase):

    def setUp(self):
        self.sender = EmailSender('mail.example.com:587', 'jf', '123')

    def test_property_smtp_server(self):
        self.assertEqual(self.sender.smtp_server, 'mail.example.com:587')

    def test_property_smtp_login(self):
        self.assertEqual(self.sender.smtp_login, 'jf')

    def test_property_smtp_password(self):
        self.assertEqual(self.sender.smtp_password, '123')

    def test_property_subject_prefix(self):
        self.assertEqual(self.sender.subject_prefix, '')

    def test_property_from_addr(self):
        self.assertEqual(
            self.sender.from_addr,
            FROM_ADDR
        )

    def test_magic_method_str(self):
        self.assertEqual(
            str(self.sender),
            '[Email sender] SMTP server mail.example.com:587, SMTP login: '
            'jf, Subject_prefix , From address: {}'.format(FROM_ADDR)
        )

    def test_method_send(self):
        with mock.patch('jflib.command_watcher.send_email') as send_email:
            self.sender.send('to@example.com', 'service', 'body')
        send_email.assert_called_with(
            body='body',
            from_addr=FROM_ADDR,
            smtp_login='jf',
            smtp_password='123',
            smtp_server='mail.example.com:587',
            subject='service',
            to_addr='to@example.com',
        )


class TestClassNscaMessage(unittest.TestCase):

    def test_method_perfomance_data(self):
        self.assertEqual(
            NscaMessage._performance_data(test=1, test_2='lol'),
            'test=1 test_2=lol'
        )

    def test_magic_method_str(self):
        message = NscaMessage(0, 'Service', 'Host')
        self.assertEqual(
            str(message),
            '[NSCA Message] Status: 0, Service name: Service, '
            'Host name: Host, Text output: SERVICE OK'
        )


class TestClassNscaSender(unittest.TestCase):

    def setUp(self):
        self.nsca = NscaSender('1.2.3.4', '1234', 1, 5667, 'Service', 'Host')

    def assert_called_with(self, mock, status, text_output):
        mock.assert_called_with(
            encryption_method=1,
            host_name='Host',
            password='1234',
            port=5667,
            remote_host='1.2.3.4',
            service_name='Service',
            status=status,
            text_output=text_output,
        )

    def send_nsca(self, *args, **kwargs):
        with mock.patch('jflib.command_watcher.send_nsca.send_nsca') as \
                send_nsca:
            self.nsca.send(*args, **kwargs)
        return send_nsca

    def test_property_remote_host(self):
        self.assertEqual(self.nsca.remote_host, '1.2.3.4')

    def test_property_password(self):
        self.assertEqual(self.nsca.password, '1234')

    def test_property_encryption_method(self):
        self.assertEqual(self.nsca.encryption_method, 1)

    def test_property_port(self):
        self.assertEqual(self.nsca.port, 5667)

    def test_property_service_name(self):
        self.assertEqual(self.nsca.service_name, 'Service')

    def test_property_host_name(self):
        self.assertEqual(self.nsca.host_name, 'Host')

    def test_magic_method_str(self):
        self.assertEqual(
            str(self.nsca),
            '[NSCA Sender] Remote host: 1.2.3.4, Encryption method: 1, '
            'Port: 5667, Service name: Service, Host name: Host'
        )

    def test_method_send_nsca(self):
        send_nsca = self.send_nsca(3, 'text', perf_1=1, perf_2='lol')
        self.assert_called_with(send_nsca, 3,
                                'SERVICE UNKNOWN - text | perf_1=1 perf_2=lol')

    def test_method_send_nsca_kwargs(self):
        send_nsca = self.send_nsca(status=3, custom_output='text', perf_1=1,
                                   perf_2='lol')
        self.assert_called_with(send_nsca, 3,
                                'SERVICE UNKNOWN - text | perf_1=1 perf_2=lol')

    def test_method_send_nsca_without_custom_output(self):
        send_nsca = self.send_nsca(0,  perf_1=1, perf_2='lol')
        self.assert_called_with(send_nsca, 0,
                                'SERVICE OK | perf_1=1 perf_2=lol')

    def test_method_send_nsca_without_custom_output_kwargs(self):
        send_nsca = self.send_nsca(status=0,  perf_1=1, perf_2='lol')
        self.assert_called_with(send_nsca, 0,
                                'SERVICE OK | perf_1=1 perf_2=lol')


class TestClassWatch(unittest.TestCase):

    def setUp(self):
        self.cmd_stderr = os.path.join(DIR_FILES, 'stderr.sh')
        self.cmd_stdout = os.path.join(DIR_FILES, 'stdout.sh')

    def test_argument_config_file(self):
        watch = Watch(config_file=CONF, service_name='test')
        self.assertEqual(watch._conf.email.to_addr, 'to@example.com')

    def test_watch_stdout(self):
        watch = Watch(config_file=CONF, service_name='test')
        with Capturing() as output:
            process = watch.run(self.cmd_stdout)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(len(output), 3)
        self.assertIn('STDOUT', output[1])
        self.assertIn('One line to stdout!', output[1])
        self.assertIn('Execution time: ', output[2])

    def test_watch_stderr(self):
        watch = Watch(config_file=CONF, service_name='test',
                      raise_exceptions=False)
        with Capturing(stream='stderr') as output:
            process = watch.run(self.cmd_stderr)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(len(output), 1)
        self.assertIn('STDERR', output[0])
        self.assertIn('One line to stderr!', output[0])

    def test_watch_run_multiple(self):
        watch = Watch(config_file=CONF, service_name='test',
                      raise_exceptions=False)
        watch.run(self.cmd_stdout)
        watch.run(self.cmd_stderr)
        self.assertEqual(len(watch._log_handler.buffer), 9)
        self.assertIn('Hostname: ', watch._log_handler.all_records)

    def test_method_run_kwargs(self):
        watch = Watch(config_file=CONF, service_name='test')
        with mock.patch('subprocess.Popen') as Popen:
            process = Popen.return_value
            process.stdout = b''
            process.stderr = b''
            process.returncode = 0
            watch.run('ls', cwd='/')
        Popen.assert_called_with(['ls'], bufsize=1, cwd='/', stderr=-1,
                                 stdout=-1)

    def test_method_run_kwargs_exception(self):
        watch = Watch(config_file=CONF, service_name='test')
        with self.assertRaises(TypeError):
            watch.run('ls', xxx=False)

    def test_property_service_name(self):
        watch = Watch(config_file=CONF, service_name='Service')
        self.assertEqual(watch._service_name, 'Service')

    def test_property_hostname(self):
        watch = Watch(config_file=CONF, service_name='test')
        self.assertEqual(watch._hostname, HOSTNAME)

    def test_property_stdout(self):
        watch = Watch(config_file=CONF, service_name='test')
        watch.log.stdout('stdout')
        self.assertEqual(watch.stdout, 'stdout')

    def test_property_stderr(self):
        watch = Watch(config_file=CONF, service_name='test')
        watch.log.stderr('stderr')
        self.assertEqual(watch.stderr, 'stderr')

    def test_property_completed_processes(self):
        watch = Watch(config_file=CONF, service_name='test')
        self.assertEqual(watch._completed_processes, [])
        watch.run(['ls'])
        watch.run(['ls', '-l'])
        watch.run(['ls', '-la'])
        self.assertEqual(len(watch._completed_processes), 3)

    def test_method_send_email_with_config_reader(self):
        watch = Watch(config_file=CONF, service_name='test')
        watch.log.info('info')
        watch.run('ls')

        with mock.patch('smtplib.SMTP') as SMTP:
            watch.send_email()

        SMTP.assert_called_with('smtp.example.com:587')
        server = SMTP.return_value
        server.login.assert_called_with('Login', 'Password')
        call_args = server.sendmail.call_args[0]
        self.assertEqual(
            call_args[0],
            'from@example.com'
        )
        self.assertEqual(call_args[1], ['to@example.com'])

        self.assertIn(
            'Subject: =?utf-8?q?command=5Fwatcher=3A_test_=28ls=29?=',
            call_args[2]
        )
        self.assertIn(
            'From: from@example.com\nTo: to@example.com\n',
            call_args[2]
        )

    def test_method_send_nsca(self):
        watch = Watch(config_file=CONF, service_name='Service')
        with mock.patch('jflib.command_watcher.send_nsca.send_nsca') as \
                send_nsca:
            watch.send_nsca(3, 'text', perf_1=1, perf_2='lol')
        send_nsca.assert_called_with(
            encryption_method=1,
            host_name=HOSTNAME,
            password='1234',
            port=5667,
            remote_host='1.2.3.4',
            service_name='Service',
            status=3,
            text_output='SERVICE UNKNOWN - text | perf_1=1 perf_2=lol'
        )
        log = 'DEBUG [NSCA Message] Status: 3, Service name: Service, ' \
              'Host name: {}, Text output: SERVICE UNKNOWN - text' \
              ' | perf_1=1 perf_2=lol'
        self.assertIn(
            log.format(HOSTNAME),
            watch._log_handler.all_records
        )

    def test_exception(self):
        watch = Watch(config_file=CONF, service_name='test')
        with self.assertRaises(CommandWatcherError):
            watch.run(self.cmd_stderr)
