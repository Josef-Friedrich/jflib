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
import queue
import shlex
import subprocess
import sys
import threading
import time
import uuid

from . import termcolor
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
        messages = []
        for record in self.buffer:
            messages.append(self.format(record))
        return '\n'.join(messages)

    def send_email(self, from_addr, to_addr, subject, smtp_login,
                   smtp_password, smtp_server):
        return send_email(from_addr=from_addr, to_addr=to_addr,
                          subject=subject, body=self.all_records,
                          smtp_login=smtp_login, smtp_password=smtp_password,
                          smtp_server=smtp_server)


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


class Watch:
    """Watch the execution of a command. Capture all output of a command.
    provide and setup a logging facility.
    """

    def __init__(self, config_file=None, config_reader=None,
                 raise_exceptions=True):
        log, log_handler = setup_logging()

        self.log = log
        """A ready to go and configured logger. An instance of
        :py:class:`logging.Logger`."""

        self._config_reader = config_reader
        if not config_reader and config_file:
            self._config_reader = ConfigReader(ini=config_file)

        self._log_handler = log_handler
        """An instance of :py:class:`LoggingHandler`."""

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

    def _build_email_subject(self):
        if self._completed_processes:
            commands = []
            for process in self._completed_processes:
                commands.append(' '.join(process.args))
        return 'command_watcher: {}'.format('; '.join(commands))

    def send_email(self, from_addr=None, to_addr=None, subject=None,
                   smtp_login=None, smtp_password=None, smtp_server=None):
        """
        :param str from_addr: The from email address.
        :param str to_addr: The to email address.
        :param str subject: The email subject.
        :param str smtp_login: The SMTP login name.
        :param str smtp_password: The SMTP password.
        :param str smtp_server: For example smtp.example.com:587
        """
        if not subject:
            subject = self._build_email_subject()
        conf = self._config_reader
        return self._log_handler.send_email(
            from_addr=from_addr if from_addr else conf.email.from_addr,
            to_addr=to_addr if to_addr else conf.email.to_addr,
            subject=subject,
            smtp_login=smtp_login if smtp_login else conf.email.smtp_login,
            smtp_password=smtp_password if smtp_password else conf.email.smtp_password,  # noqa: E501
            smtp_server=smtp_server if smtp_server else conf.email.smtp_server,
        )

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
