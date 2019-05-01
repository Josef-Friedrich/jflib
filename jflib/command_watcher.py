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

from logging.handlers import BufferingHandler
import logging
import os
import pwd
import queue
import shlex
import socket
import subprocess
import sys
import threading
import time
import uuid

from . import termcolor, send_nsca
from .config_reader import ConfigReader
from .send_email import send_email

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

CONF_DEFAULTS = {
    'email': {
        'subject_prefix': 'command_watcher',
    },
    'nsca': {
        'port': 5667,
    },
}

HOSTNAME = socket.gethostname()
USERNAME = pwd.getpwuid(os.getuid()).pw_name


class CommandWatcherError(Exception):
    """Exception raiseed by this module."""


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


class LoggingHandler(BufferingHandler):
    """Store of all logging records in the memory. Print all records on emit.
    """

    def __init__(self):
        BufferingHandler.__init__(self, capacity=1000000)

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

    def emit(self, record):
        """
        :param logging.LogRecord record: A record object.
        """
        self.buffer.append(record)
        self._print(record)
        if self.shouldFlush(record):
            self.flush()

    @property
    def stdout(self):
        """
        :param logging.LogRecord record: A record object.
        """
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


def setup_logging():
    # To get a fresh logger on each watch action.
    logger = logging.getLogger(name=str(uuid.uuid1()))
    formatter = logging.Formatter(fmt=LOGFMT, datefmt=DATEFMT)
    handler = LoggingHandler()
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


class EmailMessage:

    def __init__(self, to_addr: str, service_name: str, body: str,
                 subject_prefix: str = '', completed_processes: list = []):
        self.to_addr = to_addr
        self.subject = self._build_subject(service_name, subject_prefix,
                                           completed_processes)
        self.body = body

    @staticmethod
    def _build_subject(service_name: str, subject_prefix: str = '',
                       completed_processes: list = []):
        output = []

        # subject_prefix
        if subject_prefix:
            output.append('{}: '.format(subject_prefix))

        # service_name
        output.append(service_name)

        # commands
        commands = []
        if completed_processes:
            for process in completed_processes:
                commands.append(' '.join(process.args))
        if commands:
            output.append(' ({})'.format('; '.join(commands)))

        return ''.join(output)

    def __str__(self):
        template = '[Email Message] To address: {}, Subject: {}'
        return template.format(self.to_addr, self.subject)


class EmailSender:

    def __init__(self, smtp_server: str, smtp_login: str, smtp_password: str,
                 subject_prefix: str = '', from_addr: str = ''):
        self.smtp_server = smtp_server
        self.smtp_login = smtp_login
        self.smtp_password = smtp_password
        self.subject_prefix = subject_prefix
        self.from_addr = from_addr
        if not from_addr:
            self.from_addr = '{0} <{1}@{0}>'.format(HOSTNAME, USERNAME)

    def __str__(self):
        template = '[Email sender] SMTP server {}, SMTP login: {}, ' \
                   'Subject_prefix {}, From address: {}'
        return template.format(self.smtp_server, self.smtp_login,
                               self.subject_prefix, self.from_addr)

    def send(self, to_addr: str, service_name: str, body: str,
             completed_processes: list = []):

        message = EmailMessage(
            to_addr=to_addr,
            service_name=service_name,
            body=body,
            subject_prefix=self.subject_prefix,
            completed_processes=completed_processes
        )

        send_email(
            from_addr=self.from_addr,
            to_addr=message.to_addr,
            subject=message.subject,
            body=message.body,
            smtp_login=self.smtp_login,
            smtp_password=self.smtp_password,
            smtp_server=self.smtp_server
        )
        return message


class NscaMessage:

    def __init__(self, status: int, service_name: str, host_name: str,
                 custom_text_output: str = '', **perfdata):
        self.status = status
        self.service_name = service_name
        self.host_name = host_name
        self.text_output = self._format_text_output(
            self.status,
            custom_text_output,
            **perfdata,
        )

    def __str__(self):
        template = '[NSCA Message] Status: {}, Service name: {}, ' \
                   'Host name: {}, Text output: {}'
        return template.format(self.status, self.service_name, self.host_name,
                               self.text_output)

    @staticmethod
    def _performance_data(**perfdata) -> str:
        """
        :return: A concatenated string
        :rtype: str
        """
        pairs = []
        for key, value in perfdata.items():
            pairs.append('{!s}={!s}'.format(key, value))
        return ' '.join(pairs)

    def _format_text_output(self, status: int, custom_text_output: str = '',
                            **perfdata) -> str:
        """
        :param status: Integer describing the status
        :param custom_text_output: Freeform text placed between the prefix
          (SERVICE OK - ) and the performance data ( | perf_1=1)

        All `perfdata` gets rendered as performance data.
        """
        output_perfdata = ''
        if perfdata:
            output_perfdata = ' | {}'.format(
                self._performance_data(**perfdata)
            )

        output_prefix = '{} {}'.format(self.service_name.upper(),
                                       send_nsca.States[status])
        output_suffix = ''
        if custom_text_output:
            output_suffix = ' - {}'.format(custom_text_output)
        return '{}{}{}'.format(output_prefix, output_suffix, output_perfdata)


class NscaSender:
    """Wrapper around `send_nsca` to send NSCA messages. Set up the NSCA
    client."""

    def __init__(self, remote_host: str, password: str, encryption_method: int,
                 port: int, service_name: str, host_name: str):
        self.remote_host = remote_host
        self.password = password
        self.encryption_method = encryption_method
        self.port = port
        self.service_name = service_name
        self.host_name = host_name

    def __str__(self):
        template = '[NSCA Sender] Remote host: {}, Encryption method: {}, ' \
                   'Port: {}, Service name: {}, Host name: {}'
        return template.format(self.remote_host, self.encryption_method,
                               self.port, self.service_name, self.host_name)

    def send(self, status: int, custom_output: str = '', **kwargs):
        """Send a NSCA message to a remote NSCA server.

        :param status: Integer describing the status
        :param custom_output: Freeform text placed between the prefix
          (SERVICE OK - ) and the performance data ( | perf_1=1)

        All `kwargs` gets rendered as performance data.
        """
        message = NscaMessage(
            status=status,
            host_name=self.host_name,
            service_name=self.service_name,
            custom_text_output=custom_output,
            **kwargs
        )
        send_nsca.send_nsca(
            status=message.status,
            host_name=message.host_name,
            service_name=message.service_name,
            text_output=message.text_output,
            remote_host=self.remote_host,
            password=str(self.password),
            encryption_method=self.encryption_method,
            port=self.port,
        )
        return message


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
    def __init__(self, config_file: str, service_name: str,
                 raise_exceptions: bool = True,
                 config_reader: ConfigReader = None):
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

        if config_reader:
            self._conf = config_reader
        else:
            self._conf = ConfigReader(
                ini=config_file,
                dictionary=CONF_DEFAULTS,
            )

        self._email_sender = EmailSender(
            smtp_server=self._conf.email.smtp_server,
            smtp_login=self._conf.email.smtp_login,
            smtp_password=self._conf.email.smtp_password,
            subject_prefix=self._conf.email.subject_prefix,
            from_addr=self._conf.email.from_addr,
        )
        self.log.debug(self._email_sender)

        self._nsca_sender = NscaSender(
            remote_host=self._conf.nsca.remote_host,
            password=self._conf.nsca.password,
            encryption_method=self._conf.nsca.encryption_method,
            port=self._conf.nsca.port,
            service_name=self._service_name,
            host_name=self._hostname,
        )
        self.log.debug(self._nsca_sender)

        self._queue = queue.Queue()
        """An instance of :py:class:`queue.Queue`."""

        self._completed_processes = []
        """A list of completed processes
        :py:class:`subprocess.CompletedProcess`. Everytime you use the method
        `run()` the process object is appened in the list."""

        self._raise_exceptions = raise_exceptions
        """Raise exceptions"""

    @property
    def stdout(self):
        """Alias / shortcut for `self._log_handler.stdout`."""
        return self._log_handler.stdout

    @property
    def stderr(self):
        """Alias / shortcut for `self._log_handler.stderr`."""
        return self._log_handler.stderr

    def send_email(self):
        """
        :param str subject: The email subject.
        :param str to_addr: The to email address.
        """
        message = self._email_sender.send(
            to_addr=self._conf.email.to_addr,
            service_name=self._service_name,
            body=self._log_handler.all_records,
            completed_processes=self._completed_processes,
        )
        self.log.debug(message)

    def send_nsca(self, status: int, custom_output: str = '', **kwargs):
        """Send a NSCA message to a remote NSCA server.

        :param status: Integer describing the status
        :param custom_output: Freeform text placed between the prefix
          (SERVICE OK - ) and the performance data ( | perf_1=1)

        All `kwargs` gets render as performance data.
        """
        message = self._nsca_sender.send(
            status=status,
            custom_output=custom_output,
            **kwargs
        )
        self.log.debug(message)

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

    def run(self, args, **kwargs):
        """Run a command.

        You can use all keyword arguments from
        :py:class:`subprocess.Popen` except `bufsize`, `stderr`, `stdout`.

        :param mixed args: List or string. A command with command line
          arguments. Like subprocess.Popen(args).
        :param bool shell: If true, the command will be executed through the
          shell.
        :param str cwd: Sets the current directory before the child is
          executed.
        :param dict env: Defines the environment variables for the new process.

        :return: Process object
        :rtype: subprocess.CompletedProcess
        """
        if isinstance(args, str):
            args = shlex.split(args)
        self.log.info('Run command: {}'.format(' '.join(args)))
        timer = Timer()
        process = subprocess.Popen(args, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=1, **kwargs)

        self._start_thread(process.stdout, 'stdout')
        self._start_thread(process.stderr, 'stderr')

        for _ in range(2):
            for line, stream in iter(self._queue.get, None):
                if line:
                    line = line.decode('utf-8').strip()

                if line:
                    if stream == 'stderr':
                        self.log.stderr(line)
                    if stream == 'stdout':
                        self.log.stdout(line)

        process.wait()
        self._completed_processes.append(process)
        self.log.info('Execution time: {}'.format(timer.result()))
        if self._raise_exceptions and process.returncode != 0:
            raise CommandWatcherError(
                'The command {} exists with an non-zero return code.'
                .format(' '.join(args))
            )
        return process
