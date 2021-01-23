"""
Module to watch the execution of shell scripts. Both streams (`stdout` and
`stderr`) are captured.

.. code:: python

    watch = Watch()
    watch.log.critical(msg)
    watch.log.error(msg)
    watch.log.warning(msg)
    watch.log.info(msg)
    watch.log.debug(msg)
    watch.run(['rsync', '-av', '/home', '/backup'])
"""

import abc
import logging
import os
import pwd
import queue
import shlex
import socket
import subprocess
import shutil
import sys
import textwrap
import threading
import typing
import time
import uuid

from logging.handlers import BufferingHandler

from . import termcolor, send_nsca
from .config_reader import ConfigReader
from .send_email import send_email


HOSTNAME = socket.gethostname()
USERNAME = pwd.getpwuid(os.getuid()).pw_name


class BaseClass:

    def _obj_to_str(self, attributes=[]):
        if not attributes:
            attributes = dir(self)
        output = []
        for attribute in attributes:
            if not attribute.startswith('_') and \
               not callable(getattr(self, attribute)):
                value = getattr(self, attribute)
                if value:
                    value = textwrap.shorten(str(value), width=64)
                    value = value.replace('\n', ' ')
                    output.append('{}: \'{}\''.format(attribute, value))
        return '[{}] {}'.format(self.__class__.__name__, ', '.join(output))


class CommandWatcherError(Exception):
    """Exception raised by this module."""

    def __init__(self, msg, **data):
        reporter.report(
            status=2,
            custom_message='{}: {}'.format(self.__class__.__name__, msg),
            **data,
        )


class Timer:
    """Measure the execution time of a command run."""

    def __init__(self):
        self.stop = 0
        """"The time when the timer stops. (UNIX timestamp)"""

        self.start = time.time()
        """"The start time. (UNIX timestamp)"""

        self.interval = 0
        """The time interval between start and stop."""

    def result(self):
        """
        Measure the time intervale

        :return: A formatted string displaying the result.
        :rtype: str"""
        self.stop = time.time()
        self.interval = self.stop - self.start
        return '{:.3f}s'.format(self.interval)


# Logging #####################################################################

# CRITICAL 50
# ERROR 40
# -> STDERR 35
# WARNING 30
# INFO 20
# DEBUG 10
# --> STDOUT 5
# NOTSET 0
STDERR = 35
logging.addLevelName(STDERR, 'STDERR')
STDOUT = 5
logging.addLevelName(STDOUT, 'STDOUT')

LOGFMT = '%(asctime)s_%(msecs)03d %(levelname)s %(message)s'
DATEFMT = '%Y%m%d_%H%M%S'


class LoggingHandler(BufferingHandler):
    """Store of all logging records in the memory. Print all records on emit.
    """

    def __init__(self, master_logger=None):
        BufferingHandler.__init__(self, capacity=1000000)
        self._master_logger = master_logger

    @staticmethod
    def _print(record):
        """
        :param logging.LogRecord record: A record object.
        """
        level = record.levelname
        # CRITICAL 50
        # ERROR 40
        # -> STDERR 35
        # WARNING 30
        # INFO 20
        # DEBUG 10
        # --> STDOUT 5
        # NOTSET 0
        attr = None
        if level == 'CRITICAL':
            color = 'red'
            attr = 'bold'
        elif level == 'ERROR':
            color = 'red'
        elif level == 'STDERR':
            color = 'red'
            attr = 'dark'
        elif level == 'WARNING':
            color = 'yellow'
        elif level == 'INFO':
            color = 'green'
        elif level == 'DEBUG':
            color = 'white'
        elif level == 'STDOUT':
            color = 'white'
            attr = 'dark'
        elif level == 'NOTSET':
            color = 'grey'
        else:
            color = 'grey'

        if attr:
            reverse = ['reverse', attr]
            normal = [attr]
        else:
            reverse = ['reverse']
            normal = []

        if record.levelno >= STDERR:
            stream = sys.stderr
        else:
            stream = sys.stdout

        created = '{}_{:03d}'.format(
            time.strftime(DATEFMT, time.localtime(record.created)),
            int(record.msecs),
        )

        print('{} {} {}'.format(
            created,
            termcolor.colored(' {:<8} '.format(level), color, attrs=reverse),
            termcolor.colored(record.msg, color, attrs=normal),
        ), file=stream)

    def emit(self, record: logging.LogRecord):
        """
        :param record: A record object.
        """
        self.buffer.append(record)
        if not self._master_logger:
            self._print(record)
        else:
            self._master_logger.log(record.levelno, record.msg)
        if self.shouldFlush(record):
            self.flush()

    @property
    def stdout(self):
        messages = []
        for record in self.buffer:
            if record.levelname == 'STDOUT':
                messages.append(record.msg)
        return '\n'.join(messages)

    @property
    def stderr(self):
        messages = []
        for record in self.buffer:
            if record.levelname == 'STDERR':
                messages.append(record.msg)
        return '\n'.join(messages)

    @property
    def all_records(self):
        """All log messages joined by line breaks."""
        messages = []
        for record in self.buffer:
            messages.append(self.format(record))
        return '\n'.join(messages)


def _log_stdout(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    self._log(STDOUT, message, args, **kws)


logging.Logger.stdout = _log_stdout


def _log_stderr(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    self._log(STDERR, message, args, **kws)


logging.Logger.stderr = _log_stderr


def setup_logging(master_logger: logging.Logger = None) -> \
        typing.Tuple[logging.Logger, LoggingHandler]:
    """Setup a fresh logger for each watch action.

    :param master_logger: Forward all log messages to a master logger."""
    logger = logging.getLogger(name=str(uuid.uuid1()))
    formatter = logging.Formatter(fmt=LOGFMT, datefmt=DATEFMT)
    handler = LoggingHandler(master_logger=master_logger)
    handler.setFormatter(formatter)
    # Show all log messages: use 1 instead of 0: because:
    # From the documentation:
    # When a logger is created, the level is set to NOTSET (which causes all
    # messages to be processed when the logger is the root logger, or
    # delegation to the parent when the logger is a non-root logger). Note that
    # the root logger is created with level WARNING.
    logger.setLevel(1)
    logger.addHandler(handler)
    return (logger, handler)


# Reporting ###################################################################


class Message(BaseClass):
    """
    This message class bundles all available message data into an object. The
    different reporters can choose which data they use.

    :param int status: 0 (OK), 1 (WARNING), 2 (CRITICAL), 3 (UNKOWN): see
        Nagios / Icinga monitoring status / state.
    :param str service_name: The name of the service.
    :param str custom_message: Custom message
    :param str prefix: Prefix of the report message.
    :param str body: A longer report text.
    :param dict performance_data: A dictionary like
        `{'perf_1': 1, 'perf_2': 'test'}`.
    :param str log_records: Log records separated by new lines
    """
    def __init__(self, **data):
        self._data = data

    def __str__(self):
        return self._obj_to_str()

    @property
    def status(self) -> int:
        """0 (OK), 1 (WARNING), 2 (CRITICAL), 3 (UNKOWN): see
        Nagios / Icinga monitoring status / state."""
        return self._data.get('status', 0)

    @property
    def status_text(self) -> str:
        """The status as a text word like `OK`."""
        return send_nsca.States[self.status]

    @property
    def service_name(self) -> str:
        return self._data.get('service_name', 'service_not_set')

    @property
    def performance_data(self) -> str:
        """
        :return: A concatenated string
        :rtype: str
        """
        performance_data = self._data.get('performance_data')
        if performance_data:
            pairs = []
            for key, value in self._data.get('performance_data').items():
                pairs.append('{!s}={!s}'.format(key, value))
            return ' '.join(pairs)
        return ''

    @property
    def custom_message(self) -> str:
        return self._data.get('custom_message', '')

    @property
    def prefix(self) -> str:
        return self._data.get('prefix', '[cwatcher]:')

    @property
    def message(self) -> str:
        output = []
        if self.prefix:
            output.append(self.prefix)

        output.append(self.service_name.upper())
        output.append(self.status_text)
        if self.custom_message:
            output.append('- {}'.format(self.custom_message))
        return ' '.join(output)

    @property
    def message_monitoring(self) -> str:
        """message + performance_data"""
        output = []
        output.append(self.message)
        if self.performance_data:
            output.append('|')
            output.append(self.performance_data)
        return ' '.join(output)

    @property
    def body(self) -> str:
        """Text body for the e-mail message."""
        output = []
        output.append('Host: {}'.format(HOSTNAME))
        output.append('User: {}'.format(USERNAME))
        output.append('Service name: {}'.format(self.service_name))

        if self.performance_data:
            output.append('Performance data: {}'.format(self.performance_data))

        body = self._data.get('body', '')
        if body:
            output.append('')
            output.append(body)

        log_records = self._data.get('log_records', '')
        if log_records:
            output.append('')
            output.append('Log records:')
            output.append('')
            output.append(log_records)

        return '\n'.join(output)

    @property
    def processes(self) -> str:
        output = []
        processes = self._data.get('processes')
        if processes:
            for process in processes:
                output.append(' '.join(process.args_normalized))
        if output:
            return'({})'.format('; '.join(output))

    @property
    def user(self) -> str:
        return '[user:{}]'.format(USERNAME)


class BaseChannel(BaseClass, metaclass=abc.ABCMeta):
    """Base class for all reporters"""

    @abc.abstractmethod
    def report(self, status: int = 0, service_name: str = 'command_watcher',
               **data):
        raise NotImplementedError('A reporter class must have a `report` '
                                  'method.')


class EmailChannel(BaseChannel):
    """Send reports by e-mail."""

    def __init__(self, smtp_server: str, smtp_login: str, smtp_password: str,
                 to_addr: str, from_addr: str = '',
                 to_addr_critical: str = ''):
        self.smtp_server = smtp_server
        self.smtp_login = smtp_login
        self.smtp_password = smtp_password
        self.to_addr = to_addr
        self.from_addr = from_addr
        if not from_addr:
            self.from_addr = '{0} <{1}@{0}>'.format(HOSTNAME, USERNAME)
        self.to_addr_critical = to_addr_critical

    def __str__(self):
        return self._obj_to_str(['smtp_server', 'smtp_login', 'to_addr',
                                 'from_addr', ])

    def report(self, message: Message):
        """Send an e-mail message.

        :param message: A message object.
        """
        if message.status == 2 and self.to_addr_critical:
            to_addr = self.to_addr_critical
        else:
            to_addr = self.to_addr

        send_email(
            from_addr=self.from_addr,
            to_addr=to_addr,
            subject=message.message,
            body=message.body,
            smtp_login=self.smtp_login,
            smtp_password=self.smtp_password,
            smtp_server=self.smtp_server
        )


class NscaChannel(BaseChannel):
    """Wrapper around `send_nsca` to send NSCA messages. Set up the NSCA
    client."""

    def __init__(self, remote_host: str, password: str, encryption_method: int,
                 port: int, service_name: str):
        self.remote_host = remote_host
        self.password = password
        self.encryption_method = encryption_method
        self.port = port
        self.service_name = service_name

    def __str__(self):
        # No password!
        return self._obj_to_str(['remote_host', 'encryption_method', 'port',
                                 'service_name'])

    def report(self, message: Message):
        """Send a NSCA message to a remote NSCA server.

        :param message: A message object.
        """
        send_nsca.send_nsca(
            status=message.status,
            host_name=HOSTNAME,
            service_name=message.service_name,
            text_output=message.message_monitoring,
            remote_host=self.remote_host,
            password=str(self.password),
            encryption_method=self.encryption_method,
            port=self.port,
        )


class BeepChannel(BaseChannel):
    """Send beep sounds."""

    def __init__(self):
        self.cmd = shutil.which('beep')

    def __str__(self):
        # No password!
        return self._obj_to_str(['cmd'])

    def beep(self, frequency: float = 4186.01, length: float = 50):
        """
        Generate a beep sound using the “beep” command.

        * A success tone: frequency=4186.01, length=40
        * A failure tone: frequency=65.4064, length=100

        :param frequency: Frequency in Hz.
        :param length: Length in milliseconds.
        """
        # TODO: Use self.cmd -> Fix tests
        subprocess.run(['beep', '-f', str(float(frequency)), '-l',
                        str(float(length))])

    def report(self, message: Message):
        """Send a beep sounds.

        :param message: A message object. The only attribute that takes an
          effect is the status attribute (0-3).
        """
        if message.status == 0:  # OK
            self.beep(frequency=4186.01, length=50)  # C8 (highest note)
        elif message.status == 1:  # WARNING
            self.beep(frequency=261.626, length=100)  # C4 (middle C)
        elif message.status == 2:  # CRITICAL
            self.beep(frequency=65.4064, length=150)  # C2 (low C)
        elif message.status == 3:  # UNKOWN
            self.beep(frequency=32.7032, length=200)  # C1


class Reporter:
    """Collect all channels."""

    def __init__(self):
        self.channels = []

    def add_channel(self, channel):
        self.channels.append(channel)

    def report(self, **data):
        message = Message(**data)
        for channel in self.channels:
            channel.report(message)
        return message


reporter = Reporter()

# Configuration ###############################################################

CONF_DEFAULTS = {
    'email': {
        'subject_prefix': 'command_watcher',
    },
    'nsca': {
        'port': 5667,
    },
}


CONFIG_READER_SPEC = {
    'email': {
        'from_addr': {
            'description': 'The email address of the sender.',
        },
        'to_addr': {
            'description': 'The email address of the recipient.',
            'not_empty': True,
        },
        'to_addr_critical': {
            'description': 'The email address of the recipient to send '
                           'critical messages to.',
            'default': None,
        },
        'smtp_login': {
            'description': 'The SMTP login name.',
            'not_empty': True,
        },
        'smtp_password': {
            'description': 'The SMTP password.',
            'not_empty': True,
        },
        'smtp_server': {
            'description': 'The URL of the SMTP server, for example: '
                           '`smtp.example.com:587`.',
            'not_empty': True,
        },
    },
    'nsca': {
        'remote_host': {
            'description': 'The IP address of the NSCA remote host.',
            'not_empty': True,
        },
        'password': {
            'description': 'The NSCA password.',
            'not_empty': True,
        },
        'encryption_method': {
            'description': 'The NSCA encryption method. The supported '
                           'encryption methods are: 0 1 2 3 4 8 11 14 15 16',
            'not_empty': True,
        },
        'port': {
            'description': 'The NSCA port.',
            'default': 5667,
        },
    },
    'beep': {
        'activated': {
            'description': 'Activate the beep channel to report auditive '
                           'messages.',
            'default': False,
        }
    }
}


# Main code ###################################################################


class Process:
    """Run a process.

    You can use all keyword arguments from
    :py:class:`subprocess.Popen` except `bufsize`, `stderr`, `stdout`.

    :param args: List, tuple or string. A sequence of
        process arguments, like `subprocess.Popen(args)`.
    :param master_logger:
    :param bool shell: If true, the command will be executed through the
        shell.
    :param str cwd: Sets the current directory before the child is
        executed.
    :param dict env: Defines the environment variables for the new process.
    """
    def __init__(self, args: typing.Union[str, list, tuple],
                 master_logger: logging.Logger = None, **kwargs):
        # self.args: typing.Union[str, list, tuple] = args
        self.args = args
        """Process arguments in various types."""

        self._queue = queue.Queue()
        """An instance of :py:class:`queue.Queue`."""

        log, log_handler = setup_logging(master_logger=master_logger)
        # self.log: logging.Logger = log
        self.log = log
        """A ready to go and configured logger. An instance of
        :py:class:`logging.Logger`."""
        # self.log_handler: LoggingHandler = log_handler
        self.log_handler = log_handler
        """An instance of :py:class:`LoggingHandler`."""

        self.log.info('Run command: {}'.format(' '.join(self.args_normalized)))
        timer = Timer()
        self.subprocess = subprocess.Popen(
            self.args_normalized,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # RuntimeWarning: line buffering (buffering=1) isn't
            # supported in binary mode, the default buffer size will be used
            # bufsize=1,
            **kwargs
        )
        """subprocess"""

        self._start_thread(self.subprocess.stdout, 'stdout')
        self._start_thread(self.subprocess.stderr, 'stderr')

        for _ in range(2):
            for line, stream in iter(self._queue.get, None):
                if line:
                    line = line.decode('utf-8').strip()

                if line:
                    if stream == 'stderr':
                        self.log.stderr(line)
                    if stream == 'stdout':
                        self.log.stdout(line)
        self.subprocess.wait()
        self.log.info('Execution time: {}'.format(timer.result()))

    @property
    def args_normalized(self) -> list:
        """Normalized `args`, always a list"""
        if isinstance(self.args, str):
            return shlex.split(self.args)
        else:
            return self.args

    @property
    def stdout(self) -> str:
        """Alias / shortcut for `self.log_handler.stdout`."""
        return self.log_handler.stdout

    @property
    def line_count_stdout(self) -> int:
        """The count of lines of the current `stderr`."""
        return len(self.stdout.splitlines())

    @property
    def stderr(self) -> str:
        """Alias / shortcut for `self.log_handler.stderr`."""
        return self.log_handler.stderr

    @property
    def line_count_stderr(self) -> int:
        """The count of lines of the current `stderr`."""
        return len(self.stderr.splitlines())

    def _stdout_stderr_reader(self, pipe, stream):
        """
        :param object pipe: `process.stdout` or `process.stdout`
        :param str stream: `stdout` or `stderr`
        """
        try:
            with pipe:
                for line in iter(pipe.readline, b''):
                    self._queue.put((line, stream))
        finally:
            self._queue.put(None)

    def _start_thread(self, pipe, stream):
        """
        :param object pipe: `process.stdout` or `process.stdout`
        :param str stream: `stdout` or `stderr`
        """
        threading.Thread(
            target=self._stdout_stderr_reader,
            args=[pipe, stream]
        ).start()


class Watch:
    """Watch the execution of a command. Capture all output of a command.
    provide and setup a logging facility.

    :param config_file: The file path of the configuration file in the INI
      format.
    :param service_name: A name of the watched service.
    :param raise_exceptions: Raise exceptions if `watch.run()` exists with a
      non-zero exit code.
    :param config_reader: A custom configuration reader. Specify this
      parameter to not use the build in configuration reader.
    """
    def __init__(self, config_file: str = None,
                 service_name: str = 'command_watcher',
                 raise_exceptions: bool = True,
                 config_reader: ConfigReader = None,
                 report_channels: typing.List[BaseChannel] = None):
        self._hostname = HOSTNAME
        """The hostname of machine the watcher running on."""

        self._service_name = service_name
        """A name of the watched service."""

        log, log_handler = setup_logging()
        self.log = log
        """A ready to go and configured logger. An instance of
        :py:class:`logging.Logger`."""
        self.log.info('Hostname: {}'.format(self._hostname))
        self._log_handler = log_handler
        """An instance of :py:class:`LoggingHandler`."""

        self._conf = None
        """An instance of :py:class:`jflib.config_reader.ClassInterface`."""

        if not config_reader and config_file:
            config_reader = ConfigReader(
                spec=CONFIG_READER_SPEC,
                ini=config_file,
                dictionary=CONF_DEFAULTS,
            )

        self._conf = config_reader.get_class_interface()

        if report_channels is None:
            try:
                config_reader.check_section('email')
                email_reporter = EmailChannel(
                    smtp_server=self._conf.email.smtp_server,
                    smtp_login=self._conf.email.smtp_login,
                    smtp_password=self._conf.email.smtp_password,
                    to_addr=self._conf.email.to_addr,
                    from_addr=self._conf.email.from_addr,
                    to_addr_critical=self._conf.email.to_addr_critical,
                )
                reporter.add_channel(email_reporter)
                self.log.debug(email_reporter)
            except (ValueError, KeyError):
                pass

            try:
                config_reader.check_section('nsca')
                nsca_reporter = NscaChannel(
                    remote_host=self._conf.nsca.remote_host,
                    password=self._conf.nsca.password,
                    encryption_method=self._conf.nsca.encryption_method,
                    port=self._conf.nsca.port,
                    service_name=self._service_name,
                )
                reporter.add_channel(nsca_reporter)
                self.log.debug(nsca_reporter)
            except (ValueError, KeyError):
                pass

            if shutil.which('beep') and self._conf.beep.activated:
                beep_reporter = BeepChannel()
                reporter.add_channel(beep_reporter)
                self.log.debug(beep_reporter)

        else:
            reporter.channels = []

        self.processes = []
        """A list of completed processes
        :py:class:`Process`. Everytime you use the method
        `run()` the process object is appened in the list."""

        self._raise_exceptions = raise_exceptions
        """Raise exceptions"""

        self._timer = Timer()

    @property
    def stdout(self):
        """Alias / shortcut for `self._log_handler.stdout`."""
        return self._log_handler.stdout

    @property
    def stderr(self):
        """Alias / shortcut for `self._log_handler.stderr`."""
        return self._log_handler.stderr

    def run(self, args: typing.Union[str, list, tuple],
            log: bool = True, ignore_exceptions: typing.List[int] = [],
            **kwargs) -> Process:
        """
        Run a process.

        :param args: List, tuple or string. A sequence of
          process arguments, like `subprocess.Popen(args)`.
        :param log: Log the `stderr` and the `stdout` of the
          process. If false the `stdout` and the `stderr` are logged only
          to the local process logger, not to get global master logger.
        :param ignore_exceptions: A list of none-zero exit codes, which is
          ignored by this method.
        """
        if log:
            master_logger = self.log
        else:
            master_logger = None
        process = Process(args, master_logger=master_logger, **kwargs)
        self.processes.append(process)
        rc = process.subprocess.returncode
        if self._raise_exceptions and rc != 0 and rc not in ignore_exceptions:
            raise CommandWatcherError(
                'The command \'{}\' exists with an non-zero return code.'
                .format(' '.join(process.args_normalized)),
                service_name=self._service_name,
                log_records=self._log_handler.all_records,
            )
        return process

    def report(self, status: int, **data) -> Message:
        """Report a message using the preconfigured channels.

        :param int status: 0 (OK), 1 (WARNING), 2 (CRITICAL), 3 (UNKOWN): see
          Nagios / Icinga monitoring status / state.
        :param str custom_message: Custom message
        :param str prefix: Prefix of the report message.
        :param str body: A longer report text.
        :param dict performance_data: A dictionary like
          `{'perf_1': 1, 'perf_2': 'test'}`.
        """
        message = reporter.report(
            status=status,
            service_name=self._service_name,
            log_records=self._log_handler.all_records,
            processes=self.processes,
            **data,
        )
        self.log.debug(message)
        return message

    def final_report(self, **data) -> Message:
        """The same as the `report` method. Adds `execution_time` to the
        `performance_data`.

        :param int status: 0 (OK), 1 (WARNING), 2 (CRITICAL), 3 (UNKOWN): see
          Nagios / Icinga monitoring status / state.
        :param str custom_message: Custom message
        :param str prefix: Prefix of the report message.
        :param str body: A longer report text.
        :param dict performance_data: A dictionary like
          `{'perf_1': 1, 'perf_2': 'test'}`.
        """
        timer_result = self._timer.result()
        self.log.info(
            'Overall execution time: {}'.format(timer_result)
        )
        status = data.get('status', 0)
        data_dict = dict(data)
        if 'performance_data' not in data_dict:
            data_dict['performance_data'] = {}
        data_dict['performance_data']['execution_time'] = timer_result
        if 'status' in data_dict:
            del data_dict['status']
        return self.report(status=status, **data_dict)
