import os
import unittest
from unittest import mock

from jflib.capturing import Capturing
from jflib import command_watcher as cwatcher


DIR_FILES = os.path.join(os.path.dirname(__file__), 'files')
CONF = os.path.join(DIR_FILES, 'command_watcher', 'conf.ini')
FROM_ADDR = '{0} <{1}@{0}>'.format(cwatcher.HOSTNAME, cwatcher.USERNAME)


# Logging #####################################################################


class TestLogging(unittest.TestCase):

    def setUp(self):
        logger, handler = cwatcher.setup_logging()
        self.logger = logger
        self.handler = handler

    def test_initialisation(self):
        self.assertEqual(len(self.logger.name), 36)

    def test_log_stdout(self):
        self.logger.stdout('stdout')
        self.assertEqual(len(self.handler.buffer), 1)
        self.assertEqual(self.handler.buffer[0].msg, 'stdout')
        self.assertEqual(self.handler.buffer[0].levelname, 'STDOUT')

    def test_log_stderr(self):
        self.logger.stderr('stderr')
        self.assertEqual(len(self.handler.buffer), 1)
        self.assertEqual(self.handler.buffer[0].msg, 'stderr')
        self.assertEqual(self.handler.buffer[0].levelname, 'STDERR')

    def test_property_stdout(self):
        self.logger.stdout('line 1')
        self.logger.stdout('line 2')
        self.logger.stderr('stderr')
        self.assertEqual(self.handler.stdout, 'line 1\nline 2')

    def test_property_stderr(self):
        self.logger.stderr('line 1')
        self.logger.stderr('line 2')
        self.logger.stdout('stdout')
        self.assertEqual(self.handler.stderr, 'line 1\nline 2')

    def test_property_all_records(self):
        self.logger.stderr('stderr')
        self.logger.stdout('stdout')
        self.logger.error('error')
        self.logger.debug('debug')
        self.assertIn('stderr', self.handler.all_records)
        self.assertIn('stdout', self.handler.all_records)
        self.assertIn('error', self.handler.all_records)
        self.assertIn('debug', self.handler.all_records)


class TestColorizedPrint(unittest.TestCase):

    def setUp(self):
        self.logger, _ = cwatcher.setup_logging()

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


# Reporting ###################################################################


class TestClassMessage(unittest.TestCase):

    def setUp(self):
        process_1 = cwatcher.Process('ls')
        process_2 = cwatcher.Process(['ls', '-a'])
        self.message = cwatcher.Message(
            status=0,
            service_name='service',
            performance_data={'value1': 1, 'value2': 2},
            custom_message='Everything ok',
            processes=[process_1, process_2],
            body='A long body text.',
            log_records='1 OK \n2 Warning',
        )

    def test_property_status(self):
        self.assertEqual(self.message.status, 0)

    def test_property_status_not_set(self):
        message = cwatcher.Message()
        self.assertEqual(message.status, 0)
        self.assertEqual(message.status_text, 'OK')

    def test_property_status_text(self):
        self.assertEqual(self.message.status_text, 'OK')

    def test_property_service_name_not_set(self):
        message = cwatcher.Message()
        self.assertEqual(message.service_name, 'service_not_set')

    def test_property_performance_data(self):
        self.assertEqual(self.message.performance_data, 'value1=1 value2=2')

    def test_property_prefix(self):
        self.assertEqual(self.message.prefix, '[cwatcher]:')

    def test_property_message(self):
        self.assertEqual(self.message.message,
                         '[cwatcher]: SERVICE OK - Everything ok')

    def test_property_message_monitoring(self):
        self.assertEqual(
            self.message.message_monitoring,
            '[cwatcher]: SERVICE OK - Everything ok | value1=1 value2=2'
        )

    def test_property_body(self):
        body = 'Host: {}\n' \
               'User: {}\n' \
               'Service name: service\n' \
               'Performance data: value1=1 value2=2\n\n' \
               'A long body text.\n\nLog records:\n\n1 OK \n2 Warning'
        self.assertEqual(self.message.body,
                         body.format(cwatcher.HOSTNAME, cwatcher.USERNAME))

    def test_property_processes(self):
        self.assertEqual(self.message.processes, '(ls; ls -a)')


class TestClassEmailChannel(unittest.TestCase):

    def setUp(self):
        self.email = cwatcher.EmailChannel(
            smtp_server='mail.example.com:587',
            smtp_login='jf',
            smtp_password='123',
            to_addr='logs@example.com',
            from_addr='from@example.com',
            to_addr_critical='critical@example.com',
        )

    def test_attribute_smtp_server(self):
        self.assertEqual(self.email.smtp_server, 'mail.example.com:587')

    def test_attribute_smtp_login(self):
        self.assertEqual(self.email.smtp_login, 'jf')

    def test_attribute_smtp_password(self):
        self.assertEqual(self.email.smtp_password, '123')

    def test_attribute_to_addr(self):
        self.assertEqual(self.email.to_addr, 'logs@example.com')

    def test_attribute_from_addr(self):
        self.assertEqual(self.email.from_addr, 'from@example.com')

    def test_attribute_to_addr_critical(self):
        self.assertEqual(self.email.to_addr_critical, 'critical@example.com')

    def test_magic_method_str(self):
        self.maxDiff = None
        self.assertEqual(
            str(self.email),
            "[EmailChannel] smtp_server: 'mail.example.com:587', "
            "smtp_login: 'jf', to_addr: 'logs@example.com', "
            "from_addr: 'from@example.com'"
        )

    def test_method_report(self):
        message = cwatcher.Message(status=0, service_name='test', body='body')
        with mock.patch('jflib.command_watcher.send_email') as send_email:
            self.email.report(message)
        send_email.assert_called_with(
            body='Host: {}\nUser: {}\nService name: test\n\nbody'
                 .format(cwatcher.HOSTNAME, cwatcher.USERNAME),
            from_addr='from@example.com',
            smtp_login='jf',
            smtp_password='123',
            smtp_server='mail.example.com:587',
            subject='[cwatcher]: TEST OK',
            to_addr='logs@example.com',
        )

    def test_method_report_critical(self):
        message = cwatcher.Message(status=2, service_name='test', body='body')
        with mock.patch('jflib.command_watcher.send_email') as send_email:
            self.email.report(message)
        send_email.assert_called_with(
            body='Host: {}\nUser: {}\nService name: test\n\nbody'
                 .format(cwatcher.HOSTNAME, cwatcher.USERNAME),
            from_addr='from@example.com',
            smtp_login='jf',
            smtp_password='123',
            smtp_server='mail.example.com:587',
            subject='[cwatcher]: TEST CRITICAL',
            to_addr='critical@example.com',
        )


class TestClassNscaChannel(unittest.TestCase):

    def setUp(self):
        self.nsca = cwatcher.NscaChannel(
            remote_host='1.2.3.4',
            password='1234',
            encryption_method=1,
            port=5667,
            service_name='Service',
        )

    def assert_called_with(self, mock, status, text_output):
        mock.assert_called_with(
            encryption_method=1,
            host_name=cwatcher.HOSTNAME,
            password='1234',
            port=5667,
            remote_host='1.2.3.4',
            service_name='my_service',
            status=status,
            text_output=text_output,
        )

    def send_nsca(self, **kwargs):
        message = cwatcher.Message(service_name='my_service', prefix='',
                                   **kwargs)
        with mock.patch('jflib.command_watcher.send_nsca.send_nsca') as \
                send_nsca:
            self.nsca.report(message)
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

    def test_magic_method_str(self):
        self.assertEqual(
            str(self.nsca),
            "[NscaChannel] remote_host: '1.2.3.4', encryption_method: '1', "
            "port: '5667', service_name: 'Service'"
        )

    def test_method_send_nsca(self):
        send_nsca = self.send_nsca(
            status=3,
            custom_message='text',
            performance_data={'perf_1': 1, 'perf_2': 'lol'}
        )
        self.assert_called_with(
            send_nsca, 3, 'MY_SERVICE UNKNOWN - text | perf_1=1 perf_2=lol')

    def test_method_send_nsca_kwargs(self):
        send_nsca = self.send_nsca(
            status=3,
            custom_message='text',
            performance_data={'perf_1': 1, 'perf_2': 'lol'}
        )
        self.assert_called_with(
            send_nsca, 3, 'MY_SERVICE UNKNOWN - text | perf_1=1 perf_2=lol'
        )

    def test_method_send_nsca_without_custom_output(self):
        send_nsca = self.send_nsca(
            status=0,
            performance_data={'perf_1': 1, 'perf_2': 'lol'}
        )
        self.assert_called_with(send_nsca, 0,
                                'MY_SERVICE OK | perf_1=1 perf_2=lol')

    def test_method_send_nsca_without_custom_output_kwargs(self):
        send_nsca = self.send_nsca(
            status=0,
            performance_data={'perf_1': 1, 'perf_2': 'lol'}
        )
        self.assert_called_with(
            send_nsca, 0, 'MY_SERVICE OK | perf_1=1 perf_2=lol'
        )


class TestClassBeepChannel(unittest.TestCase):

    def setUp(self):
        self.beep = cwatcher.BeepChannel()

    def report(self, status):
        message = cwatcher.Message(service_name='my_service', prefix='',
                                   status=status)
        with mock.patch('subprocess.run') as subprocess_run:
            self.beep.report(message)
        return subprocess_run

    def test_status_ok(self):
        subprocess_run = self.report(0)
        subprocess_run.assert_called_with(
            ['beep', '-f', '4186.01', '-l', '50.0']
        )

    def test_status_warning(self):
        subprocess_run = self.report(1)
        subprocess_run.assert_called_with(
            ['beep', '-f', '261.626', '-l', '100.0']
        )

    def test_status_critical(self):
        subprocess_run = self.report(2)
        subprocess_run.assert_called_with(
            ['beep', '-f', '65.4064', '-l', '150.0']
        )

    def test_status_unkown(self):
        subprocess_run = self.report(3)
        subprocess_run.assert_called_with(
            ['beep', '-f', '32.7032', '-l', '200.0']
        )

# Main code ###################################################################


class TestClassProcess(unittest.TestCase):

    def setUp(self):
        self.cmd_stderr = os.path.join(DIR_FILES, 'stderr.sh')
        self.cmd_stdout = os.path.join(DIR_FILES, 'stdout.sh')

    def launch_process(self, *args, **kwargs):
        return cwatcher.Process(*args, **kwargs)

    def test_attribute_args(self):
        process = self.launch_process('ls -l')
        self.assertEqual(process.args, 'ls -l')

    def test_attribute_log(self):
        process = self.launch_process('ls -l')
        self.assertEqual(process.log.__class__.__name__, 'Logger')

    def test_attribute_log_handler(self):
        process = self.launch_process('ls -l')
        self.assertEqual(process.log_handler.__class__.__name__,
                         'LoggingHandler')

    def test_attribute_subprocess(self):
        process = self.launch_process('ls -l')
        self.assertEqual(process.subprocess.__class__.__name__,
                         'Popen')

    def test_property_args_normalized(self):
        process = self.launch_process('ls -l')
        self.assertEqual(process.args_normalized, ['ls', '-l'])

    def test_property_stdout(self):
        process = self.launch_process([self.cmd_stdout])
        self.assertTrue(process.stdout)

    def test_property_line_count_stdout(self):
        process = self.launch_process([self.cmd_stdout])
        self.assertEqual(process.line_count_stdout, 1)
        self.assertEqual(process.line_count_stderr, 0)

    def test_property_stderr(self):
        process = self.launch_process([self.cmd_stderr])
        self.assertTrue(process.stderr)

    def test_property_line_count_stderr(self):
        process = self.launch_process([self.cmd_stderr])
        self.assertEqual(process.line_count_stdout, 0)
        self.assertEqual(process.line_count_stderr, 1)


class TestClassWatch(unittest.TestCase):

    def setUp(self):
        self.cmd_stderr = os.path.join(DIR_FILES, 'stderr.sh')
        self.cmd_stdout = os.path.join(DIR_FILES, 'stdout.sh')

    def test_argument_config_file(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test')
        self.assertEqual(watch._conf.email.to_addr, 'to@example.com')

    def test_method_run_output_stdout(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test')
        with Capturing() as output:
            process = watch.run(self.cmd_stdout)
        self.assertEqual(process.subprocess.returncode, 0)
        self.assertEqual(len(output), 3)
        self.assertIn('STDOUT', output[1])
        self.assertIn('One line to stdout!', output[1])
        self.assertIn('Execution time: ', output[2])

    def test_method_run_output_stderr(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test',
                               raise_exceptions=False, )
        with Capturing(stream='stderr') as output:
            process = watch.run(self.cmd_stderr)
        self.assertEqual(process.subprocess.returncode, 1)
        # On travis
        # ['Exception in thread Thread-59:', 'Trace[993 chars][0m'] != ''
        # self.assertEqual(len(output), 1)
        self.assertIn('STDERR', output.tostring())
        self.assertIn('One line to stderr!', output.tostring())

    def test_method_run_multiple(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test',
                               raise_exceptions=False)
        watch.run(self.cmd_stdout)
        watch.run(self.cmd_stderr)
        self.assertEqual(len(watch._log_handler.buffer), 9)
        self.assertIn('Hostname: ', watch._log_handler.all_records)

    def test_method_run_log_true(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test',
                               raise_exceptions=False)
        process = watch.run(self.cmd_stdout, log=True)
        self.assertEqual(watch.stdout, 'One line to stdout!')
        self.assertEqual(process.stdout, 'One line to stdout!')

    def test_method_run_log_false(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test',
                               raise_exceptions=False)
        process = watch.run(self.cmd_stdout, log=False)
        self.assertEqual(watch.stdout, '')
        self.assertEqual(process.stdout, 'One line to stdout!')

    def test_method_run_kwargs(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test')
        with mock.patch('subprocess.Popen') as Popen:
            process = Popen.return_value
            process.stdout = b''
            process.stderr = b''
            process.returncode = 0
            watch.run('ls', cwd='/')
        Popen.assert_called_with(['ls'], cwd='/', stderr=-1,
                                 stdout=-1)

    def test_method_run_kwargs_exception(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test')
        with self.assertRaises(TypeError):
            watch.run('ls', xxx=False)

    def test_property_service_name(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='Service')
        self.assertEqual(watch._service_name, 'Service')

    def test_property_hostname(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test')
        self.assertEqual(watch._hostname, cwatcher.HOSTNAME)

    def test_property_stdout(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test')
        watch.log.stdout('stdout')
        self.assertEqual(watch.stdout, 'stdout')

    def test_property_stderr(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test')
        watch.log.stderr('stderr')
        self.assertEqual(watch.stderr, 'stderr')

    def test_propertyprocesses(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test')
        self.assertEqual(watch.processes, [])
        watch.run(['ls'])
        watch.run(['ls', '-l'])
        watch.run(['ls', '-la'])
        self.assertEqual(len(watch.processes), 3)

    def test_method_report_channel_email(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='my_service')
        watch.log.info('info')
        watch.run('ls')

        with mock.patch('jflib.command_watcher.send_nsca.send_nsca'), \
                mock.patch('smtplib.SMTP') as SMTP:
            watch.report(
                status=0,
                custom_message='My message',
                performance_data={'perf_1': 1, 'perf_2': 'test'},
                prefix='',
            )

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
            'From: from@example.com\nTo: to@example.com\n',
            call_args[2]
        )

    def test_method_report_channel_email_critical(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='my_service')
        with mock.patch('jflib.command_watcher.send_nsca.send_nsca'), \
                mock.patch('smtplib.SMTP') as SMTP:
            watch.report(status=2)
        server = SMTP.return_value
        call_args = server.sendmail.call_args[0]
        self.assertEqual(call_args[1], ['critical@example.com'])
        self.assertIn(
            'From: from@example.com\nTo: critical@example.com\n',
            call_args[2]
        )

    def test_method_report_channel_nsca(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='my_service')
        with mock.patch('jflib.command_watcher.send_nsca.send_nsca') as \
                send_nsca, \
                mock.patch('jflib.command_watcher.send_email'):
            watch.report(
                status=0,
                custom_message='My message',
                performance_data={'perf_1': 1, 'perf_2': 'test'},
                prefix='',
            )
        send_nsca.assert_called_with(
            encryption_method=1,
            host_name=cwatcher.HOSTNAME,
            password='1234',
            port=5667,
            remote_host='1.2.3.4',
            service_name='my_service',
            status=0,
            text_output='MY_SERVICE OK - My message | perf_1=1 perf_2=test'
        )

        records = watch._log_handler.all_records
        self.assertIn('DEBUG [Message]', records)
        self.assertIn("custom_message: 'My message',", records)
        self.assertIn("message: 'MY_SERVICE OK - My message',", records)
        self.assertIn(
            "message_monitoring: 'MY_SERVICE OK - My message | "
            "perf_1=1 perf_2=test',",
            records
        )
        self.assertIn("performance_data: 'perf_1=1 perf_2=test'", records)
        self.assertIn("service_name: 'my_service',", records)
        self.assertIn("status_text: 'OK',", records)
        self.assertIn("user: '[user:{}]'".format(cwatcher.USERNAME), records)

    def test_exception(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test',
                               report_channels=[])
        with self.assertRaises(cwatcher.CommandWatcherError):
            watch.run(self.cmd_stderr)

    def test_ignore_exceptions(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test',
                               report_channels=[])
        process = watch.run(self.cmd_stderr, ignore_exceptions=[1])
        self.assertEqual(process.subprocess.returncode, 1)

    def test_ignore_exceptions_raise(self):
        watch = cwatcher.Watch(config_file=CONF, service_name='test',
                               report_channels=[])
        with self.assertRaises(cwatcher.CommandWatcherError):
            watch.run(os.path.join(DIR_FILES, 'exit-2.sh'),
                      ignore_exceptions=[1])


class TestClassWatchMethodFinalReport(unittest.TestCase):

    def final_report(self, **data):
        watch = cwatcher.Watch(config_file=CONF, service_name='test',
                               report_channels=[])
        watch._timer.result = mock.Mock()
        watch._timer.result.return_value = '11.123s'
        return watch.final_report(**data)

    def test_without_arguments(self):
        message = self.final_report()
        self.assertEqual(message.status, 0)
        self.assertEqual(message.message, '[cwatcher]: TEST OK')
        self.assertEqual(message.message_monitoring,
                         '[cwatcher]: TEST OK | execution_time=11.123s')

    def test_with_arguments(self):
        message = self.final_report(status=1, custom_message='test')
        self.assertEqual(message.status, 1)
        self.assertEqual(message.message, '[cwatcher]: TEST WARNING - test')
